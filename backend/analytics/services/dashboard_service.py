from typing import Dict, List, Any, Optional
from datetime import date, timedelta, datetime, time
from collections import defaultdict

from django.db.models import Count, Sum
from django.utils.timezone import make_aware
from django.db.models.functions import TruncDate

from core.models import Clinic
from inventory.models import PrescriptionLine, DrugMaster
from analytics.models import Appointment
from .insights_service import InsightsService
from .forecasting import ForecastingService
from .restock_service import RestockService
from .usage import UsageIntelligence
from ..utils.logger import get_logger
from ..services.aggregation import get_disease_type
from ..utils.filters import apply_clinic_filter

# Configuration Constants
COMPLETION_RATE_ESTIMATE = 0.85
TOP_DISEASES_DISPLAY_LIMIT = 10
TOP_FORECASTS_DISPLAY_LIMIT = 2
TOP_RESTOCK_DISPLAY_LIMIT = 5
TOP_CLINICS_DISPLAY_LIMIT = 10
TOP_LEVEL_INSIGHTS_LIMIT = 5
RESTOCK_DECISION_WINDOW_DAYS = 7
DEFAULT_TOP_DRUGS_LIMIT = 50

logger = get_logger(__name__)

class DashboardService:
    """Consolidated service with isolated logic for dashboard fragments."""

    @staticmethod
    def _get_appt_context(days: int, request=None) -> Dict[str, Any]:
        """Shared helper to get isolated appointment data context using ORM aggregation."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        start_dt = make_aware(datetime.combine(start_date, time.min))
        end_dt = make_aware(datetime.combine(end_date, time.max))
        
        appt_qs_base = Appointment.objects.filter(
            appointment_datetime__range=(start_dt, end_dt), 
            disease__isnull=False
        )
        
        # Optimized: Aggregate at the DB level first using SQL GROUP BY
        appt_qs = (
            apply_clinic_filter(appt_qs_base, request)
            .annotate(day=TruncDate('appointment_datetime'))
            .values('day', 'disease__name', 'disease__season')
            .annotate(count=Count('id'))
        )
        
        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season = {}
        
        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            day = row['day']
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][day] += row['count']
            
        return {
            'daily_by_dtype': daily_by_dtype,
            'dtype_season': dtype_season,
            'start_date': start_date,
            'end_date': end_date
        }

    @classmethod
    def get_stats_fragment(cls, days: int = 30, request=None) -> Dict[str, Any]:
        """LIGHTWEIGHT: Only returns top-level counters."""
        try:
            ctx = cls._get_appt_context(days, request)
            total = sum(sum(day_map.values()) for day_map in ctx['daily_by_dtype'].values())
            return {
                'total_appointments': total,
                'completed_cases': int(total * COMPLETION_RATE_ESTIMATE),
                'active_outbreaks': 0, # Placeholder for specific stat-only view
                'risk_status': 'Stable'
            }
        except Exception as e:
            logger.error(f"Failed to get stats fragment: {str(e)}", exc_info=True)
            return {'error': 'Stats retrieval failed'}

    @classmethod
    def get_trends_fragment(cls, days: int = 30, forecast_days: int = 8, request=None) -> Dict[str, Any]:
        """MODERATE: Only returns forecasting and strategic insights."""
        try:
            ctx = cls._get_appt_context(days, request)
            forecasting = ForecastingService()
            insights_service = InsightsService()
            
            # Defensive buffer initialization for sub-services
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
                        'count': int(d.get('historical_avg', 0) * days),
                        'trend_score': d.get('forecast_value', 0),
                        'trend_direction': d.get('trend', 'stable').title(),
                    } for d in top_disease_forecasts[:TOP_DISEASES_DISPLAY_LIMIT]
                ],
                'forecasts': [
                    {
                        'name': d['disease_name'],
                        'predicted_cases': d['forecast_value'],
                        'forecast_period': f'Next {d["days_ahead"]} days'
                    } for d in top_disease_forecasts[:TOP_FORECASTS_DISPLAY_LIMIT]
                ],
                'insights': strategic_insights
            }
        except Exception as e:
            logger.error(f"Failed to get trends fragment: {str(e)}", exc_info=True)
            return {'error': 'Trend retrieval failed'}

    @classmethod
    def get_medicines_fragment(cls, days: int = 30, request=None) -> List[Dict[str, Any]]:
        """HEAVY: Isolated high-volume prescription analytics."""
        try:
            ctx = cls._get_appt_context(days, request)
            restock_service = RestockService()
            end_date = date.today()
            decide_start_date = end_date - timedelta(days=RESTOCK_DECISION_WINDOW_DAYS)

            top_rx_qs_base = PrescriptionLine.objects.filter(
                prescription_date__range=(decide_start_date, end_date)
            )
            
            top_ids_qs = (
                apply_clinic_filter(top_rx_qs_base, request, clinic_field='prescription__clinic')
                .values('drug_id')
                .annotate(total=Sum('quantity'))
                .order_by('-total')[:DEFAULT_TOP_DRUGS_LIMIT]
            )
            
            top_ids = [d['drug_id'] for d in top_ids_qs]
            
            if not top_ids:
                return []

            dm_qs_base = DrugMaster.objects.filter(id__in=top_ids)
            drug_names_map = {d.id: d.drug_name for d in apply_clinic_filter(dm_qs_base, request)}
            
            ctx['top_medicines_data'] = drug_names_map
            ctx['decision_window_start'] = decide_start_date
            ctx['buffer_info'] = {'adaptive_buffer': 0}

            restock_suggestions = restock_service.calculate_restock_suggestions(
                decide_start_date, end_date, precalculated_context=ctx, request=request
            )
            
            return [
                {
                    'drug': s['drug_name'],
                    'current_stock': s['current_stock'],
                    'predicted_demand': round(s['predicted_demand'], 1),
                    'status': s['status'].title(),
                    'priority': 'High' if s['status'].lower() == 'critical' else 'Normal',
                    'recommended_restock': s['suggested_restock']
                } 
                for s in restock_suggestions[:TOP_RESTOCK_DISPLAY_LIMIT]
            ]
        except Exception as e:
            logger.error(f"Failed to get medicines fragment: {str(e)}", exc_info=True)
            return []

    @classmethod
    def get_multi_level_insights(cls, days: int = 30, request=None) -> Dict[str, Any]:
        """
        FEATURE 9: Multi-Level Analytics Dashboard.
        Provides insights at clinic, doctor, and disease level.
        """
        try:
            ctx = cls._get_appt_context(days, request)
            usage_intel = UsageIntelligence()
            
            # 1. Disease Level (Rising, Seasonal, Forecasts)
            forecasting = ForecastingService()
            disease_forecasts = forecasting.forecast_all_diseases(days_ahead=7, precalculated_context=ctx)
            
            # 2. Doctor Level (Performance)
            doctor_patterns = usage_intel.get_doctor_patterns(days=days)
            
            # 3. Clinic Level (District/Clinic specific)
            clinic_stats = []
            # Performance: Fetch clinics with minimal fields to reduce I/O
            clinics = Clinic.objects.all().only('clinic_name', 'clinic_address_1')[:TOP_CLINICS_DISPLAY_LIMIT]
            for clinic in clinics:
                clinic_stats.append({
                    'clinic_name': clinic.clinic_name,
                    'location': clinic.clinic_address_1,
                    'status': 'Operational'
                })

            return {
                'disease_level': disease_forecasts[:TOP_LEVEL_INSIGHTS_LIMIT],
                'doctor_level': doctor_patterns[:TOP_LEVEL_INSIGHTS_LIMIT] if isinstance(doctor_patterns, list) else [doctor_patterns],
                'clinic_level': clinic_stats
            }
        except Exception as e:
            logger.error(f"Failed to get multi-level insights: {str(e)}", exc_info=True)
            return {'error': 'Multi-level insight retrieval failed'}

    @classmethod
    def get_unified_dashboard(cls, days: int = 30, forecast_days: int = 8, request=None) -> Dict[str, Any]:
        """COMPREHENSIVE: Orchestrates a single source of truth for the platform."""
        try:
            stats = cls.get_stats_fragment(days, request)
            trends = cls.get_trends_fragment(days, forecast_days, request)
            medicines = cls.get_medicines_fragment(days, request)
            multi_level = cls.get_multi_level_insights(days, request)
            
            return {
                'analytics': stats,
                'top_diseases': trends.get('top_diseases', []),
                'forecasts': trends.get('forecasts', []),
                'insights': trends.get('insights', []),
                'decisions': medicines,
                'multi_level': multi_level
            }
        except Exception as e:
            logger.error(f"Failed to get unified dashboard: {str(e)}", exc_info=True)
            return {'error': 'Unified dashboard retrieval failed'}
