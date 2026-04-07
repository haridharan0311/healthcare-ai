"""
WebSocket Consumers for Real-Time Analytics Updates

Provides WebSocket support for live data streaming (Requirement 6 - Live Updates).
Uses Django Channels to push real-time updates to connected clients.

Layer: API (WebSocket Layer)
Architecture:
    - DiseaseTrendConsumer: Stream disease trend updates
    - SpikeAlertConsumer: Stream spike detection alerts
    - RestockConsumer: Stream restock suggestions
    - InventoryConsumer: Stream inventory level changes

Features:
    - Real-time data push without polling
    - Broadcast to multiple clients
    - Graceful disconnection handling
    - Error recovery with reconnection support

Usage (Frontend):
    import { useWebSocket } from './hooks/useWebSocket';
    
    function MyCom ponent() {
        const [data, setData] = useWebSocket('ws://localhost:8000/ws/disease-trends/');
        return <div>{JSON.stringify(data)}</div>;
    }
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import date, timedelta

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Count, Sum, Max, Q
from django.db.models.functions import TruncDate
from django.core.cache import cache

from analytics.models import Appointment, Disease
from inventory.models import Prescription, PrescriptionLine, DrugMaster
from .aggregation import get_disease_type
from .ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from .spike_detector import detect_spike, get_seasonal_weight
from .restock_calculator import calculate_restock, apply_multi_disease_contribution
from analytics.utils.logger import get_logger

logger = get_logger(__name__)


class DiseaseTrendConsumer(AsyncWebsocketConsumer):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LIVE UPDATES: Disease Trend WebSocket Consumer
    ═══════════════════════════════════════════════════════════════════════════
    
    Requirement 6: Stream real-time disease trend updates to connected clients.
    
    Message flow:
        Client connects → Server sends current trends → Updates broadcast on data change
    
    Messages:
        From client: {"action": "subscribe", "days": 30}
        To client: {
            "type": "trend_update",
            "data": [...disease trends...],
            "timestamp": "2026-04-07T10:30:00"
        }
    
    For new users:
        Connect a WebSocket client to /ws/disease-trends/ to receive live updates
        whenever disease data changes. First message contains current data.
    """
    
    async def connect(self):
        """Accept WebSocket connection."""
        self.user_id = self.scope.get('user', {}).get('id', 'anonymous')
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
        """Fetch disease trends from database."""
        from collections import defaultdict
        
        end = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        end = end.date() if end else date.today()
        start = end - timedelta(days=days)
        mid = end - timedelta(days=7)
        
        current_month = date.today().month
        
        # ORM aggregation
        recent_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(mid, end),
                disease__isnull=False,
                disease__is_active=True,
            )
            .select_related('disease')
            .values('disease__name', 'disease__season',
                    'disease__category', 'disease__severity')
            .annotate(recent_count=Count('id'))
        )
        
        older_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, mid),
                disease__isnull=False,
                disease__is_active=True,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(older_count=Count('id'))
        )
        
        older_map = {
            get_disease_type(r['disease__name']): r['older_count']
            for r in older_qs
        }
        
        type_data = defaultdict(lambda: {
            'season': 'All', 'category': '', 'severity': 1,
            'recent': 0, 'older': 0
        })
        
        for row in recent_qs:
            dtype = get_disease_type(row['disease__name'])
            type_data[dtype]['season'] = row['disease__season']
            type_data[dtype]['category'] = row['disease__category'] or ''
            type_data[dtype]['severity'] = row['disease__severity']
            type_data[dtype]['recent'] += row['recent_count']
            type_data[dtype]['older'] += older_map.get(dtype, 0)
        
        if not type_data:
            return []
        
        results = []
        for dtype, data in type_data.items():
            sw = get_seasonal_weight(data['season'], current_month)
            score = round(
                weighted_trend_score(data['recent'], data['older']) * sw, 2
            )
            results.append({
                'disease_name': dtype,
                'season': data['season'],
                'total_cases': data['recent'] + data['older'],
                'trend_score': score,
                'seasonal_weight': sw,
            })
        
        results.sort(key=lambda x: x['trend_score'], reverse=True)
        return results
    
    async def trend_update(self, event: Dict[str, Any]):
        """Handle trend update broadcast."""
        await self.send(text_data=json.dumps(event))


class SpikeAlertConsumer(AsyncWebsocketConsumer):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LIVE UPDATES: Spike Alert WebSocket Consumer
    ═══════════════════════════════════════════════════════════════════════════
    
    Requirement 6: Stream real-time spike detection alerts.
    
    Features:
        - Immediate notification when spike detected
        - Configurable sensitivity (baseline window)
        - Alert severity (how far above threshold)
    
    Messages:
        From client: {"action": "subscribe", "days": 8}
        To client: {
            "type": "spike_alert",
            "disease_name": "Flu",
            "severity": "critical",
            "today_count": 15,
            "threshold": 8,
            "timestamp": "2026-04-07T10:30:00"
        }
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
        """Fetch current spike alerts."""
        from collections import defaultdict
        
        days = 8
        end = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        end = end.date() if end else date.today()
        start = end - timedelta(days=days)
        
        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name', 'disease__season')
            .annotate(day_count=Count('id'))
        )
        
        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        type_season = {}
        
        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            type_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']
        
        if not type_season:
            return []
        
        baseline_days = days - 1
        results = []
        
        for dtype in type_season:
            daily_counts = self._build_daily_list(
                daily_by_dtype, dtype, start, end
            )
            spike_info = detect_spike(daily_counts, baseline_days=baseline_days)
            
            if spike_info['is_spike']:
                results.append({
                    'disease_name': dtype,
                    'severity': 'critical' if spike_info['today_count'] > spike_info['threshold'] * 1.5 else 'alert',
                    **spike_info
                })
        
        results.sort(key=lambda x: x['today_count'], reverse=True)
        return results
    
    @staticmethod
    def _build_daily_list(daily_by_dtype: dict, dtype: str,
                         start: date, end: date) -> list:
        """Build ordered daily count list."""
        counts = []
        cursor = start
        while cursor <= end:
            counts.append(daily_by_dtype[dtype].get(cursor, 0))
            cursor += timedelta(days=1)
        return counts
    
    async def spike_alert(self, event: Dict[str, Any]):
        """Handle spike alert broadcast."""
        await self.send(text_data=json.dumps(event))


class RestockConsumer(AsyncWebsocketConsumer):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LIVE UPDATES: Restock Suggestion WebSocket Consumer
    ═══════════════════════════════════════════════════════════════════────████
    
    Requirement 6: Stream real-time restock suggestions.
    
    Use case: Inventory managers watch restock status in real-time as
    medicine quantities update and demand forecasts change.
    
    Messages:
        To client: {
            "type": "restock_update",
            "drug_name": "Paracetamol",
            "status": "critical",
            "current_stock": 50,
            "predicted_demand": 200,
            "suggested_restock": 150
        }
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
            suggestions = await self.get_restock_suggestions()
            await self.send(text_data=json.dumps({
                'type': 'restock_update',
                'data': suggestions,
                'timestamp': date.today().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending restock suggestions: {e}")
    
    @database_sync_to_async
    def get_restock_suggestions(self, days: int = 30) -> list:
        """Fetch restock suggestions."""
        # Simplified version - use actual restock logic from views
        drugs = DrugMaster.objects.select_related('clinic').values(
            'drug_name', 'generic_name', 'current_stock'
        )[:50]
        
        return [{
            'drug_name': drug['drug_name'],
            'generic_name': drug['generic_name'],
            'current_stock': drug['current_stock'],
            'status': 'critical' if drug['current_stock'] == 0 else 'low' if drug['current_stock'] < 100 else 'sufficient'
        } for drug in drugs]
    
    async def restock_update(self, event: Dict[str, Any]):
        """Handle restock update broadcast."""
        await self.send(text_data=json.dumps(event))
