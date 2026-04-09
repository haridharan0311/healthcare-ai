import json
from datetime import date, timedelta
from typing import Dict, Any

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Max

from analytics.models import Appointment
from analytics.services.restock_service import RestockService
from analytics.utils.logger import get_logger

logger = get_logger(__name__)


class RestockConsumer(AsyncWebsocketConsumer):
    """
    LIVE UPDATES: Restock Suggestion WebSocket Consumer
    Streams real-time restock suggestions computed by the central Service layer.
    """
    
    async def connect(self):
        """Accept WebSocket connection."""
        await self.channel_layer.group_add('restock_updates', self.channel_name)
        await self.accept()
        
        # Send initial restock data
        await self.send_restock_suggestions()
    
    async def disconnect(self, close_code):
        """Handle disconnection."""
        await self.channel_layer.group_discard('restock_updates', self.channel_name)
    
    async def receive(self, text_data: str):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            if data.get('action') == 'refresh':
                await self.send_restock_suggestions()
        except Exception as e:
            logger.error(f"Error in restock consumer: {e}")
    
    async def send_restock_suggestions(self):
        """Send current restock suggestions."""
        try:
            suggestions = await self.get_restock_suggestions(days=30)
            await self.send(text_data=json.dumps({
                'type': 'restock_update',
                'data': suggestions[:15], # Limit to top 15 most urgent via websocket
                'timestamp': date.today().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending restock suggestions: {e}")
            
    @database_sync_to_async
    def get_restock_suggestions(self, days: int = 30) -> list:
        """Fetch restock suggestions using RestockService."""
        end = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        end_date = end.date() if end else date.today()
        start_date = end_date - timedelta(days=days)

        service = RestockService()
        return service.calculate_restock_suggestions(start_date, end_date)
    
    async def restock_update(self, event: Dict[str, Any]):
        """Handle restock update broadcast."""
        await self.send(text_data=json.dumps(event))
