import json
from datetime import date, timedelta
from typing import Dict, Any

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Max

from analytics.models import Appointment
from analytics.services.disease_analytics import DiseaseAnalyticsService
from analytics.utils.logger import get_logger

logger = get_logger(__name__)


class DiseaseTrendConsumer(AsyncWebsocketConsumer):
    """
    LIVE UPDATES: Disease Trend WebSocket Consumer
    Streams real-time disease trend updates to connected clients using the central Service layer.
    """
    
    async def connect(self):
        """Accept WebSocket connection."""
        user = self.scope.get('user')
        self.user_id = getattr(user, 'id', 'anonymous') if user else 'anonymous'
        self.days = 30
        
        await self.channel_layer.group_add('disease_trends', self.channel_name)
        await self.accept()
        
        logger.info(
            f"Disease trend client connected: {self.user_id}",
            extra={'user': self.user_id, 'channel': self.channel_name}
        )
        
        # Send initial data
        await self.send_disease_trends()
    
    async def disconnect(self, close_code):
        """Handle disconnection."""
        await self.channel_layer.group_discard('disease_trends', self.channel_name)
        logger.info(
            f"Disease trend client disconnected: {self.user_id}",
            extra={'user': self.user_id, 'code': close_code}
        )
    
    async def receive(self, text_data: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action', 'update')
            
            if action == 'subscribe':
                self.days = data.get('days', 30)
                await self.send_disease_trends()
            elif action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in disease trends consumer")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
        except Exception as e:
            logger.error(f"Error in disease trends consumer: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def send_disease_trends(self):
        """Query and send disease trends."""
        try:
            trends = await self.get_disease_trends(self.days)
            await self.send(text_data=json.dumps({
                'type': 'trend_update',
                'data': trends,
                'timestamp': date.today().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending disease trends: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Failed to fetch trends: {str(e)}"
            }))
    
    @database_sync_to_async
    def get_disease_trends(self, days: int = 30) -> list:
        """Fetch disease trends using DiseaseAnalyticsService."""
        end = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        end_date = end.date() if end else date.today()
        start_date = end_date - timedelta(days=days)

        service = DiseaseAnalyticsService()
        return service.get_all_disease_trends(start_date, end_date)
    
    async def trend_update(self, event: Dict[str, Any]):
        """Handle trend update broadcast."""
        await self.send(text_data=json.dumps(event))
