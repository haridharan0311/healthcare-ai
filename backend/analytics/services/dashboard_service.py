from typing import Dict, List, Any
from datetime import date, timedelta, datetime, time
from collections import defaultdict

from .insights_service import InsightsService
from .forecasting import ForecastingService
from .restock_service import RestockService
from inventory.models import PrescriptionLine, DrugMaster
from analytics.models import Appointment
from django.db.models import Count, Sum
from ..utils.logger import get_logger
from ..services.aggregation import get_disease_type

logger = get_logger(__name__)

class DashboardService:
    """Consolidated service with isolated logic for dashboard fragments."""

    @staticmethod
    def _get_appt_context(days: int):
        """Shared helper to get isolated appointment data context."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        
        appt_qs = (
            Appointment.objects
            .filter(appointment_datetime__range=(start_dt, end_dt), disease__isnull=False)
            .values('appointment_datetime', 'disease__name', 'disease__season')
        )
        
        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season = {}
        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            day = row['appointment_datetime'].date()
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][day] += 1
            
        return {
            'daily_by_dtype': daily_by_dtype,
            'dtype_season': dtype_season,
            'start_date': start_date,
            'end_date': end_date
        }

    @classmethod
    def get_stats_fragment(cls, days: int = 30) -> Dict:
        """LIGHTWEIGHT: Only returns top-level counters."""
        ctx = cls._get_appt_context(days)
        total = sum(sum(day_map.values()) for day_map in ctx['daily_by_dtype'].values())
        return {
            'total_appointments': total,
            'completed_cases': total * 0.85,
            'active_outbreaks': 0, # Simplified for stats-only
            'risk_status': 'Stable'
        }

    @classmethod
    def get_trends_fragment(cls, days: int = 30, forecast_days: int = 8) -> Dict:
        """MODERATE: Only returns forecasting and strategic insights."""
        ctx = cls._get_appt_context(days)
        forecasting = ForecastingService()
        insights_service = InsightsService()
        
        # We need a minimal buffer_info for the insights service to not crash
        ctx['buffer_info'] = {'adaptive_buffer': 0}
        
        top_disease_forecasts = forecasting.forecast_all_diseases(
            days_ahead=forecast_days, precalculated_context=ctx
        )
        strategic_insights = insights_service.get_actionable_insights(
            days=days, precalculated_context=ctx
        )
        
        return {
            'top_diseases': [
                {
                    'name': d['disease_name'],
                    'count': d.get('historical_avg', 0) * 30,
                    'trend_score': d.get('forecast_value', 0),
                    'trend_direction': d.get('trend', 'stable').title(),
                } for d in top_disease_forecasts[:10]
            ],
            'forecasts': [
                {
                    'name': d['disease_name'],
                    'predicted_cases': d['forecast_value'],
                    'forecast_period': f'Next {d["days_ahead"]} days'
                } for d in top_disease_forecasts[:2]
            ],
            'insights': strategic_insights
        }

    @classmethod
    def get_medicines_fragment(cls, days: int = 30) -> List[Dict]:
        """HEAVY: Isolated 2.8M row prescription analytics."""
        ctx = cls._get_appt_context(days)
        restock_service = RestockService()
        end_date = date.today()
        decide_start_date = end_date - timedelta(days=7) # Sample window

        top_ids_qs = (
            PrescriptionLine.objects
            .filter(prescription_date__range=(decide_start_date, end_date))
            .values('drug_id')
            .annotate(total=Sum('quantity'))
            .order_by('-total')[:50] # Reduced limit for dashboard
        )
        top_ids = [d['drug_id'] for d in top_ids_qs]
        drug_names_map = {d.id: d.drug_name for d in DrugMaster.objects.filter(id__in=top_ids)}
        
        ctx['top_medicines_data'] = drug_names_map
        ctx['decision_window_start'] = decide_start_date
        ctx['buffer_info'] = {'adaptive_buffer': 0}

        restock_suggestions = restock_service.calculate_restock_suggestions(
            decide_start_date, end_date, precalculated_context=ctx
        )
        
        return [{
            'drug': s['drug_name'],
            'current_stock': s['current_stock'],
            'predicted_demand': round(s['predicted_demand'], 1),
            'status': s['status'].title(),
            'priority': 'High' if s['status'] == 'critical' else 'Normal',
            'recommended_restock': s['suggested_restock']
        } for s in restock_suggestions[:5]]
