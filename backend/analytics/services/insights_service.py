"""
Insights Service Module
=======================

Decision Layer: Consolidated intelligence derived from Analytics and Prediction layers.
Implements Feature 1, 2, 4, 8, 9, 10 for the Decision-Support platform.
"""

from typing import List, Dict, Any
from datetime import date, timedelta
from collections import defaultdict

from .aggregation import aggregate_daily_counts, aggregate_disease_counts, get_disease_type
from .forecasting import ForecastingService
from .restock_service import RestockService
from .usage import UsageIntelligence
from .spike_detection import detect_spike_logic as detect_spike
from ..utils.logger import get_logger

logger = get_logger(__name__)

class InsightsService:
    """Consolidated intelligence service for decision support."""

    def __init__(self):
        self.forecasting = ForecastingService()
        self.restock = RestockService()
        self.usage_intel = UsageIntelligence()

    def get_actionable_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        FEATURE 9, 10: Generate structured actionable insights across all levels.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 1. Outbreak Alerts (Feature 2, 8)
        outbreaks = self._detect_active_outbreaks(start_date, end_date)

        # 2. Rising Threats (Feature 1: Growth Rate)
        growth_trends = self._calculate_growth_rates(days)

        # 3. Critical Resource Decisions (Feature 4, 5, 8)
        stock_alerts = self.usage_intel.get_stock_alerts()
        buffer_info = self.restock.calculate_adaptive_buffer(start_date, end_date)

        return {
            'outbreaks': outbreaks,
            'rising_trends': growth_trends[:5],
            'critical_stock': stock_alerts[:5],
            'recommendations': self._generate_strategic_recommendations(outbreaks, growth_trends, stock_alerts, buffer_info),
            'metadata': {
                'period_days': days,
                'safety_buffer': buffer_info['adaptive_buffer'],
                'risk_level': buffer_info['interpretation']
            }
        }

    def get_unified_alert_stream(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        FEATURE 8: Unified Real-Time Alert System.
        Aggregates all critical events into a prioritize stream.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        alerts = []

        # 1. Outbreak Alerts (High Priority)
        outbreaks = self._detect_active_outbreaks(start_date, end_date)
        for o in outbreaks:
            alerts.append({
                'type': 'outbreak',
                'priority': 'Critical' if o['severity'] == 'Critical' else 'High',
                'title': f"{o['severity']} Outbreak: {o['disease']}",
                'message': o['message'],
                'data': o,
                'timestamp': date.today().isoformat()
            })

        # 2. Stock Shortage Alerts (Direct Inventory Risk)
        stock_alerts = self.usage_intel.get_stock_alerts(critical_threshold=20)
        for s in stock_alerts:
            if s['status'] == 'critical':
                alerts.append({
                    'type': 'stock',
                    'priority': 'Critical',
                    'title': f"Inventory Depleted: {s['drug_name']}",
                    'message': f"Immediate restock required for {s['drug_name']} at {s['clinic']}.",
                    'data': s,
                    'timestamp': date.today().isoformat()
                })

        # 3. Forecast Depletion Warnings (Predictive Risk)
        # Check top 10 used drugs for depletion
        top_drugs = self.usage_intel.get_stock_alerts(low_threshold=500)[:10]
        for drug in top_drugs:
            depletion = self.forecasting.forecast_stock_depletion(drug['drug_name'])
            if depletion.get('status') == 'critical':
                alerts.append({
                    'type': 'depletion',
                    'priority': 'High',
                    'title': f"Predicted Stockout: {drug['drug_name']}",
                    'message': depletion.get('recommendation'),
                    'data': depletion,
                    'timestamp': date.today().isoformat()
                })

        # Sort by Priority: Critical > High > Warning
        PRIO_MAP = {'Critical': 0, 'High': 1, 'Warning': 2, 'normal': 3}
        return sorted(alerts, key=lambda x: PRIO_MAP.get(x['priority'], 9))

    def _detect_active_outbreaks(self, start: date, end: date) -> List[Dict]:
        """Detect diseases shows continuous upward trends or significant spikes."""
        daily_map = aggregate_daily_counts(start, end)
        outbreaks = []

        for dtype, data in daily_map.items():
            daily_list = [data['daily'].get(start + timedelta(days=i), 0) for i in range((end - start).days + 1)]
            if len(daily_list) < 7: continue

            spike_info = detect_spike(daily_list)
            if spike_info['is_spike']:
                outbreaks.append({
                    'disease': dtype,
                    'severity': 'Critical' if spike_info['today_count'] > spike_info['threshold'] * 1.5 else 'Warning',
                    'current_cases': spike_info['today_count'],
                    'expected_normal': round(spike_info['mean_last_7_days'], 1),
                    'message': f"Significant spike in {dtype} detected today."
                })
        
        return sorted(outbreaks, key=lambda x: x['current_cases'], reverse=True)

    def _calculate_growth_rates(self, days: int) -> List[Dict]:
        """Feature 1: Calculate % change in case volume across windows."""
        return self.usage_intel.get_all_disease_trends(days=days)

    def _generate_strategic_recommendations(self, outbreaks, trends, stock, buffer) -> List[str]:
        """Feature 10: Logical inference for actionable steps."""
        actions = []
        
        if outbreaks:
            actions.append(f"Deploy emergency resources for {', '.join([o['disease'] for o in outbreaks[:2]])}.")
        
        if buffer['adaptive_buffer'] > 1.4:
            actions.append(f"System-wide risk level is {buffer['interpretation'].upper()}. Increase safety buffers to {buffer['adaptive_buffer']}.")
        
        top_growth = [t['disease'] for t in trends if t.get('growth_rate', 0) > 20]
        if top_growth:
            actions.append(f"Proactively restock medicines for fast-growing diseases: {', '.join(top_growth[:3])}.")

        critical_stock = [s['drug_name'] for s in stock if s['status'] == 'critical']
        if critical_stock:
            actions.append(f"CRITICAL: Immediate restock required for {', '.join(critical_stock[:3])}.")

        return actions
