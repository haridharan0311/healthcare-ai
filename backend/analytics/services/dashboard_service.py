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
        Coordinates multi-layer analysis to provide a high-level platform summary.
        Flow: Decision Layer -> Predicition Layer -> Analytics Layer.
        """
        logger.info(f"Generating tiered dashboard summary for last {days} days")
        
        # 1. Prediction & Decision Layers (The "Insights")
        insights_service = InsightsService()
        forecasting = ForecastingService()
        
        strategic_insights = insights_service.get_actionable_insights(days=days)
        
        # 2. Disease Highlights (Analytics + Prediction)
        top_disease_forecasts = forecasting.forecast_all_diseases(days_ahead=forecast_days)
        
        # 3. Decision Support (Medicine/Restock)
        # Using modular restock service instead of Raw SQL logic
        restock_service = RestockService()
        restock_suggestions = restock_service.calculate_restock_suggestions()
        
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

