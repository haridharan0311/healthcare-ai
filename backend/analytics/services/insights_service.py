"""
Insights Service Module
=======================

Decision Layer: Consolidated intelligence derived from Analytics and Prediction layers.
Implements Feature 1, 2, 4, 8, 9, 10 for the Decision-Support platform.
"""

from typing import List, Dict, Any, Optional
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

    def get_actionable_insights(self, days: int = 30, precalculated_context: Optional[Dict] = None, request=None) -> Dict[str, Any]:
        """
        FEATURE 9, 10: Generate structured actionable insights.
        Optimized: Uses precalculated context to avoid 3x redundant scans.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        ctx = precalculated_context or {}

        # 1. Outbreak Alerts (Feature 2, 8)
        if 'outbreaks' in ctx:
            outbreaks = ctx['outbreaks']
        else:
            outbreaks = self._detect_active_outbreaks(start_date, end_date, context=ctx, request=request)

        # 2. Rising Threats (Feature 1: Growth Rate)
        growth_trends = self._calculate_growth_rates(days, request=request)

        # 3. Critical Resource Decisions (Feature 4, 5, 8)
        stock_alerts = self.usage_intel.get_stock_alerts(request=request)
        
        if 'buffer_info' in ctx:
            buffer_info = ctx['buffer_info']
        else:
            daily_by_dtype = ctx.get('daily_by_dtype')
            buffer_info = self.restock.calculate_adaptive_buffer(start_date, end_date, daily_by_disease=daily_by_dtype, request=request)

        return {
            'outbreaks': outbreaks,
            'rising_trends': growth_trends[:5],
            'critical_stock': stock_alerts[:5],
            'recommendations': self._generate_strategic_recommendations(outbreaks, growth_trends, stock_alerts, buffer_info),
            'metadata': {
                'period_days': days,
                'safety_buffer': buffer_info.get('adaptive_buffer', 0),
                'risk_level': buffer_info.get('interpretation', 'Unknown')
            }
        }

    def get_unified_alert_stream(self, days: int = 14, request=None) -> List[Dict[str, Any]]:
        """
        FEATURE 8: Unified Real-Time Alert System.
        Aggregates all critical events into a prioritize stream.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        alerts = []

        # 1. Outbreak Alerts (High Priority)
        outbreaks = self._detect_active_outbreaks(start_date, end_date, request=request)
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
        stock_alerts = self.usage_intel.get_stock_alerts(critical_threshold=20, request=request)
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
        top_drugs = self.usage_intel.get_stock_alerts(low_threshold=500, request=request)[:10]
        for drug in top_drugs:
            depletion = self.forecasting.forecast_stock_depletion(drug['drug_name'], request=request)
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

    def _detect_active_outbreaks(self, start: date, end: date, context: Optional[Dict] = None, request=None) -> List[Dict]:
        """Detect diseases shows continuous upward trends or significant spikes."""
        ctx = context or {}
        if 'daily_by_dtype' in ctx:
            daily_map = ctx['daily_by_dtype']
        else:
            from ..views.utils import apply_clinic_filter
            from analytics.models import Appointment
            appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
            daily_map = aggregate_daily_counts(start, end, queryset=appt_qs)
        
        outbreaks = []
        for dtype, data in daily_map.items():
            # Handle both aggregate_daily_counts format and our custom context format
            daily_dict = data.get('daily', data) if isinstance(data, dict) else data
            daily_list = [daily_dict.get(start + timedelta(days=i), 0) for i in range((end - start).days + 1)]
            
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

    def _calculate_growth_rates(self, days: int, request=None) -> List[Dict]:
        """Feature 1: Calculate % change in case volume across windows."""
        from analytics.models import Appointment
        from ..views.utils import apply_clinic_filter
        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        return self.usage_intel.get_all_disease_trends(days=days, appt_queryset=appt_qs)

    def _generate_strategic_recommendations(self, outbreaks, trends, stock, buffer) -> List[str]:
        """
        FEATURE 10: Logical inference for actionable steps.
        Optimized: Declarative rule-based engine for better readability and scaling.
        """
        recommendations = []
        
        # Rule 1: Outbreak response
        if outbreaks:
            names = [o['disease'] for o in outbreaks[:2]]
            recommendations.append(f"Deploy emergency resources for {', '.join(names)}.")
            
        # Rule 2: Adaptive Buffer adjustment
        if buffer.get('adaptive_buffer', 0) > 1.4:
            level = buffer.get('interpretation', 'unknown').upper()
            val = buffer.get('adaptive_buffer')
            recommendations.append(f"System-wide risk level is {level}. Increase safety buffers to {val}.")
            
        # Rule 3: Proactive restock for high-growth diseases
        top_growth = [t['disease_name'] for t in trends if t.get('growth_rate', 0) > 20]
        if top_growth:
            recommendations.append(f"Proactively restock medicines for fast-growing diseases: {', '.join(top_growth[:3])}.")
            
        # Rule 4: Immediate stockouts
        critical_drugs = [s['drug_name'] for s in stock if s.get('status') == 'critical']
        if critical_drugs:
            recommendations.append(f"CRITICAL: Immediate restock required for {', '.join(critical_drugs[:3])}.")
            
        return recommendations
