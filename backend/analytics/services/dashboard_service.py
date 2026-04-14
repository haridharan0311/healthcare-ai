"""
Dashboard Service - Tiered Architecture Implementation
======================================================
Coordinates data flow from Database -> Analytics -> Prediction -> Decision.
"""

from typing import Dict, List, Any
from datetime import date, timedelta

from .insights_service import InsightsService
from .forecasting import ForecastingService
from .restock_service import RestockService
from ..utils.logger import get_logger

logger = get_logger(__name__)

class DashboardService:
    """Consolidated service coordinating multiple analytics layers."""

    @staticmethod
    def get_unified_dashboard(days: int = 30, forecast_days: int = 8) -> Dict[str, Any]:
        """
        Coordinates multi-layer analysis with optimized data context.
        Consolidates redundant scans into a single high-performance pass.
        """
        from analytics.models import Appointment
        from django.db.models import Count
        from ..services.aggregation import get_disease_type
        from collections import defaultdict
        
        logger.info(f"Generating optimized tiered dashboard: last {days} days")
        
        # ─── DATA CONTEXT PREPARATION (THE PERFORMANCE FIX) ────────────
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Single DB pass for all historical case counts
        appt_qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start_date, end_date), disease__isnull=False)
            .values('appointment_datetime__date', 'disease__name', 'disease__season')
            .annotate(day_count=Count('id'))
        )
        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season = {}
        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appointment_datetime__date']] += row['day_count']
            
        # Shared Context for Services
        context = {
            'daily_by_dtype': daily_by_dtype,
            'dtype_season': dtype_season,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # 1. Prediction & Decision Layers (The "Insights")
        insights_service = InsightsService()
        forecasting = ForecastingService()
        restock_service = RestockService()
        
        # Pre-calculated buffer info (Feature 5) passed to all layers
        buffer_info = restock_service.calculate_adaptive_buffer(
            start_date, end_date, daily_by_disease=daily_by_dtype
        )
        context['buffer_info'] = buffer_info
        
        strategic_insights = insights_service.get_actionable_insights(
            days=days, precalculated_context=context
        )
        
        # 2. Disease Highlights (Analytics + Prediction)
        top_disease_forecasts = forecasting.forecast_all_diseases(days_ahead=forecast_days)
        
        # 3. Decision Support (Medicine/Restock)
        restock_suggestions = restock_service.calculate_restock_suggestions(
            start_date, end_date, precalculated_context=context
        )
        
        # Format for Dashboard UI compatibility
        decisions = []
        for s in restock_suggestions[:5]:
            decisions.append({
                'drug': s['drug_name'],
                'current_stock': s['current_stock'],
                'predicted_demand': round(s['predicted_demand'], 1),
                'status': s['status'].title(),
                'priority': 'High' if s['status'] == 'critical' else 'Normal',
                'recommended_restock': s['suggested_restock']
            })

        return {
            'analytics': {
                'total_appointments': sum(d.get('total', 0) for d in top_disease_forecasts),
                'completed_cases': sum(d.get('total', 0) for d in top_disease_forecasts) * 0.85, # Estimated
                'active_outbreaks': len(strategic_insights['outbreaks']),
                'risk_status': strategic_insights['metadata']['risk_level']
            },
            'top_diseases': [
                {
                    'name': d['disease_name'],
                    'count': d.get('historical_avg', 0) * 30, # Backwards estimate
                    'trend_score': d.get('forecast_value', 0),
                    'trend_direction': d.get('trend', 'stable').title(),
                    'severity': 1 # Placeholder
                } for d in top_disease_forecasts[:5]
            ],
            'forecasts': [
                {
                    'name': d['disease_name'],
                    'predicted_cases': d['forecast_value'],
                    'forecast_period': f'Next {d["days_ahead"]} days'
                } for d in top_disease_forecasts[:2]
            ],
            'decisions': decisions,
            'insights': strategic_insights, # NEW: High level intelligence block
            'metadata': { 
                'mode': 'Tiered Architecture V4',
                'layers_active': ['Decision', 'Prediction', 'Analytics']
            }
        }

