import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)

class SpikeAlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time spike alerts.
    Allows clients to subscribe to a 'spikes' group to receive instant notifications.
    """
    async def connect(self):
        self.group_name = "spikes"
        
        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket Connected: {self.channel_name}")

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"WebSocket Disconnected: {self.channel_name}")

    async def receive(self, text_data):
        # Handle messages from the client if needed (currently read-only push)
        pass

    async def spike_notification(self, event):
        """
        Send a spike notification to the client.
        Called when a message is sent to the 'spikes' group.
        """
        await self.send(text_data=json.dumps({
            'type': 'spike_alert',
            'data': event['data']
        }))
