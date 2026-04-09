import json
from datetime import date
from typing import Dict, Any

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from analytics.services.spike_detection import SpikeDetectionService
from analytics.utils.logger import get_logger

logger = get_logger(__name__)


class SpikeAlertConsumer(AsyncWebsocketConsumer):
    """
    LIVE UPDATES: Spike Alert WebSocket Consumer
    Streams real-time spike detection alerts using the central Service layer.
    """
    
    async def connect(self):
        """Accept WebSocket connection."""
        await self.channel_layer.group_add('spike_alerts', self.channel_name)
        await self.accept()
        
        # Send initial spike data
        await self.send_spike_alerts()
    
    async def disconnect(self, close_code):
        """Handle disconnection."""
        await self.channel_layer.group_discard('spike_alerts', self.channel_name)
    
    async def receive(self, text_data: str):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action', 'update')
            
            if action == 'refresh':
                await self.send_spike_alerts()
        except Exception as e:
            logger.error(f"Error in spike alert consumer: {e}")
    
    async def send_spike_alerts(self):
        """Query and send spike alerts."""
        try:
            alerts = await self.get_spike_alerts()
            await self.send(text_data=json.dumps({
                'type': 'spike_alerts',
                'data': alerts,
                'timestamp': date.today().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending spike alerts: {e}")
    
    @database_sync_to_async
    def get_spike_alerts(self) -> list:
        """Fetch current spike alerts using SpikeDetectionService."""
        service = SpikeDetectionService()
        return service.generate_spike_alerts()
    
    async def spike_alert(self, event: Dict[str, Any]):
        """Handle spike alert broadcast."""
        await self.send(text_data=json.dumps(event))
