"""
Alert Engine Service
====================

Unifies spikes, stock issues, and abnormal trends into a single priority-sorted stream.
Implements Feature 8.
"""

from typing import List, Dict, Any
from datetime import date, timedelta
from .spike_detection import SpikeDetectionService
from .forecasting import ForecastingService
from .usage import UsageIntelligence
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AlertEngineService:
    def __init__(self):
        self.spike_service = SpikeDetectionService()
        self.forecast_service = ForecastingService()
        self.usage_intel = UsageIntelligence()

    def get_unified_alerts(self, days: int = 14, request=None) -> List[Dict[str, Any]]:
        """
        Aggregates alerts from multiple sources and ranks them by priority.
        """
        alerts = []
        
        # 1. Outbreak Alerts (Early Warning)
        outbreaks = self.spike_service.detect_early_outbreaks(min_days=3, min_cases=5)
        for o in outbreaks:
            alerts.append({
                'type': 'outbreak',
                'priority': 'Critical' if o['severity'] == 'critical' else 'High',
                'title': f"Early Outbreak Detected: {o['disease_name']}",
                'message': o['message'],
                'data': o,
                'impact_score': o['impact_score'],
                'timestamp': date.today().isoformat()
            })

        # 2. Stock Depletion Alerts (Inventory Risk)
        # Check top drugs for depletion within 7 days
        stock_alerts = self.usage_intel.get_stock_alerts(critical_threshold=10, low_threshold=50, request=request)
        for s in stock_alerts:
            # For each low stock drug, check when it will hit zero
            depletion = self.forecast_service.forecast_stock_depletion(s['drug_name'], days=days, request=request)
            if depletion['status'] == 'critical' or depletion['days_until_depletion'] < 7:
                alerts.append({
                    'type': 'stock',
                    'priority': 'Critical',
                    'title': f"Critical Stock Shortage: {s['drug_name']}",
                    'message': depletion['recommendation'],
                    'data': depletion,
                    'impact_score': 90.0,
                    'timestamp': date.today().isoformat()
                })

        # 3. Growth Rate Spikes (Rising Threats)
        from .timeseries import TimeSeriesAnalysis
        ts = TimeSeriesAnalysis()
        from analytics.models import Disease
        
        active_diseases = Disease.objects.filter(is_active=True).values_list('name', flat=True).distinct()
        for dname in active_diseases:
            growth = ts.calculate_growth_rate(dname, days=7)
            if growth.get('status') == 'rising':
                alerts.append({
                    'type': 'growth',
                    'priority': 'High',
                    'title': f"Rapid Growth: {dname}",
                    'message': f"{dname} cases increased by {growth['growth_rate']}% in the last 7 days.",
                    'data': growth,
                    'impact_score': growth['growth_rate'] * 0.5,
                    'timestamp': date.today().isoformat()
                })

        # Sort by impact score
        return sorted(alerts, key=lambda x: x['impact_score'], reverse=True)
