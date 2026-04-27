"""
Insights Service Module
=======================

Decision Layer: Consolidated intelligence derived from Analytics and Prediction layers.
Implements Feature 1, 2, 4, 8, 9, 10 for the Decision-Support platform.
"""

from typing import List, Dict, Any, Optional
from datetime import timedelta
from django.utils import timezone

from analytics.models import Appointment
from .aggregation import aggregate_daily_counts
from .forecasting import ForecastingService
from .restock_service import RestockService
from .usage import UsageIntelligence
from .spike_detection import detect_spike_logic as detect_spike
from .timeseries import TimeSeriesAnalysis
from ..utils.logger import get_logger
from ..utils.filters import apply_clinic_filter

# Configuration Constants
DEFAULT_INSIGHT_DAYS = 30
DEFAULT_ALERT_DAYS = 14
CRITICAL_STOCK_THRESHOLD = 20
LOW_STOCK_THRESHOLD = 500
FORECAST_HORIZON_DAYS = 7
SPIKE_SEVERITY_MULTIPLIER = 1.5
ADAPTIVE_BUFFER_THRESHOLD = 1.4

# Priority levels
PRIORITY_CRITICAL = 'Critical'
PRIORITY_HIGH = 'High'
PRIORITY_WARNING = 'Warning'
PRIORITY_NORMAL = 'normal'

PRIO_MAP = {
    PRIORITY_CRITICAL: 0,
    PRIORITY_HIGH: 1,
    PRIORITY_WARNING: 2,
    PRIORITY_NORMAL: 3
}

logger = get_logger(__name__)

class InsightsService:
    """Consolidated intelligence service for decision support."""

    def __init__(self):
        self.forecasting = ForecastingService()
        self.restock = RestockService()
        self.usage_intel = UsageIntelligence()
        self.timeseries = TimeSeriesAnalysis()

    def get_actionable_insights(
        self, 
        days: int = DEFAULT_INSIGHT_DAYS, 
        precalculated_context: Optional[Dict] = None, 
        request=None
    ) -> Dict[str, Any]:
        """
        FEATURE 9, 10: Generate structured actionable insights.
        Uses precalculated context to optimize performance and avoid redundant DB scans.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        ctx = precalculated_context or {}

        try:
            # 1. Outbreak Alerts (Feature 2, 8)
            outbreaks = ctx.get('outbreaks') or self._detect_active_outbreaks(
                start_date, end_date, context=ctx, request=request
            )

            # 2. Rising Threats (Feature 1: Growth Rate)
            growth_trends = self._calculate_growth_rates(days, request=request)

            # 3. Critical Resource Decisions (Feature 4, 5, 8)
            stock_alerts = self.usage_intel.get_stock_alerts(request=request)
            
            if 'buffer_info' in ctx:
                buffer_info = ctx['buffer_info']
            else:
                daily_by_dtype = ctx.get('daily_by_dtype')
                buffer_info = self.restock.calculate_adaptive_buffer(
                    start_date, 
                    end_date, 
                    daily_by_disease=daily_by_dtype, 
                    request=request
                )

            return {
                'outbreaks': outbreaks,
                'rising_trends': growth_trends[:5],
                'critical_stock': stock_alerts[:5],
                'recommendations': self._generate_strategic_recommendations(
                    outbreaks, growth_trends, stock_alerts, buffer_info
                ),
                'metadata': {
                    'period_days': days,
                    'safety_buffer': buffer_info.get('adaptive_buffer', 0),
                    'risk_level': buffer_info.get('interpretation', 'Unknown')
                }
            }
        except Exception as e:
            logger.error(f"Error generating actionable insights: {str(e)}", exc_info=True)
            return {
                'outbreaks': [],
                'rising_trends': [],
                'critical_stock': [],
                'recommendations': ["System error: Unable to generate recommendations."],
                'metadata': {'period_days': days, 'safety_buffer': 0, 'risk_level': 'ERROR'}
            }

    def get_unified_alert_stream(self, days: int = DEFAULT_ALERT_DAYS, request=None) -> List[Dict[str, Any]]:
        """
        FEATURE 8: Unified Real-Time Alert System.
        Aggregates all critical events into a prioritized stream.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        alerts = []

        try:
            # 1. Outbreak Alerts (High Priority)
            outbreaks = self._detect_active_outbreaks(start_date, end_date, request=request)
            for o in outbreaks:
                prio = PRIORITY_CRITICAL if o['severity'] == PRIORITY_CRITICAL else PRIORITY_HIGH
                alerts.append({
                    'type': 'outbreak',
                    'priority': prio,
                    'title': f"{o['severity']} Outbreak: {o.get('disease')}",
                    'message': o.get('message'),
                    'data': o,
                    'timestamp': end_date.isoformat()
                })

            # 2. Stock Shortage Alerts (Direct Inventory Risk)
            stock_alerts = self.usage_intel.get_stock_alerts(
                critical_threshold=CRITICAL_STOCK_THRESHOLD, 
                request=request
            )
            for s in stock_alerts:
                if s.get('status') == 'critical':
                    alerts.append({
                        'type': 'stock',
                        'priority': PRIORITY_CRITICAL,
                        'title': f"Inventory Depleted: {s.get('drug_name')}",
                        'message': f"Immediate restock required for {s.get('drug_name')} at {s.get('clinic')}.",
                        'data': s,
                        'timestamp': end_date.isoformat()
                    })

            # 3. Forecast Depletion Warnings (Predictive Risk)
            appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
            growth_map = self.timeseries.calculate_bulk_growth_rates(
                days=FORECAST_HORIZON_DAYS, 
                appt_queryset=appt_qs
            )
            
            top_drugs = self.usage_intel.get_stock_alerts(
                low_threshold=LOW_STOCK_THRESHOLD, 
                request=request
            )[:10]
            
            for drug in top_drugs:
                depletion = self.forecasting.forecast_stock_depletion(
                    drug.get('drug_name'), 
                    request=request, 
                    growth_map=growth_map
                )
                if depletion.get('status') == 'critical':
                    alerts.append({
                        'type': 'depletion',
                        'priority': PRIORITY_HIGH,
                        'title': f"Predicted Stockout: {drug.get('drug_name')}",
                        'message': depletion.get('recommendation'),
                        'data': depletion,
                        'timestamp': end_date.isoformat()
                    })

            return sorted(alerts, key=lambda x: PRIO_MAP.get(x['priority'], 9))
            
        except Exception as e:
            logger.error(f"Error generating alert stream: {str(e)}", exc_info=True)
            return []

    def _detect_active_outbreaks(
        self, 
        start: timezone.now().date(), 
        end: timezone.now().date(), 
        context: Optional[Dict] = None, 
        request=None
    ) -> List[Dict]:
        """Detect diseases showing continuous upward trends or significant spikes."""
        ctx = context or {}
        try:
            if 'daily_by_dtype' in ctx:
                daily_map = ctx['daily_by_dtype']
            else:
                appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
                daily_map = aggregate_daily_counts(start, end, queryset=appt_qs)
            
            outbreaks = []
            for dtype, data in daily_map.items():
                daily_dict = data.get('daily', data) if isinstance(data, dict) else data
                daily_list = [daily_dict.get(start + timedelta(days=i), 0) for i in range((end - start).days + 1)]
                
                if len(daily_list) < 7:
                    continue

                spike_info = detect_spike(daily_list)
                if spike_info['is_spike']:
                    severity = PRIORITY_CRITICAL if spike_info['today_count'] > spike_info['threshold'] * SPIKE_SEVERITY_MULTIPLIER else PRIORITY_WARNING
                    outbreaks.append({
                        'disease': dtype,
                        'severity': severity,
                        'current_cases': spike_info['today_count'],
                        'expected_normal': round(spike_info['mean_last_7_days'], 1),
                        'message': f"Significant spike in {dtype} detected today."
                    })
            
            return sorted(outbreaks, key=lambda x: x['current_cases'], reverse=True)
        except Exception as e:
            logger.error(f"Error in outbreak detection: {str(e)}", exc_info=True)
            return []

    def _calculate_growth_rates(self, days: int, request=None) -> List[Dict]:
        """Feature 1: Calculate % change in case volume across windows."""
        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        return self.usage_intel.get_all_disease_trends(days=days, appt_queryset=appt_qs)

    def _generate_strategic_recommendations(self, outbreaks, trends, stock, buffer) -> List[str]:
        """
        FEATURE 10: Logical inference for actionable steps.
        Rule-based engine for strategic recommendations.
        """
        recommendations = []
        
        if outbreaks:
            names = [o.get('disease') for o in outbreaks[:2]]
            recommendations.append(f"Deploy emergency resources for {', '.join(filter(None, names))}.")
            
        adaptive_buffer = buffer.get('adaptive_buffer', 0)
        if adaptive_buffer > ADAPTIVE_BUFFER_THRESHOLD:
            level = buffer.get('interpretation', 'unknown').upper()
            recommendations.append(f"System-wide risk level is {level}. Increase safety buffers to {adaptive_buffer}.")
            
        top_growth = [t.get('disease_name') for t in trends if t.get('growth_rate', 0) > 20]
        if top_growth:
            recommendations.append(f"Proactively restock medicines for fast-growing diseases: {', '.join(top_growth[:3])}.")
            
        critical_drugs = [s.get('drug_name') for s in stock if s.get('status') == 'critical']
        if critical_drugs:
            recommendations.append(f"CRITICAL: Immediate restock required for {', '.join(critical_drugs[:3])}.")
            
        return recommendations

