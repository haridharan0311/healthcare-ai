"""
Centralized Analytics Service Facade
====================================
Unified entry point for all analytics, predictions, and decision-support logic.
This service orchestrates communication between specialized modules to provide 
high-level insights to the API layer.
"""

from typing import Dict, Any, Optional

from .timeseries import TimeSeriesAnalysis
from .restock_service import RestockService
from .forecasting import ForecastingService
from .insights_service import InsightsService
from .usage import UsageIntelligence
from ..utils.logger import get_logger

# Constants for Analytics Service Configuration
DEFAULT_STATUS_LOOKBACK_DAYS = 30
DEFAULT_FORECAST_HORIZON_DAYS = 7
DEFAULT_ANALYTICS_DAYS = 30
DEFAULT_SEASONALITY_SCOPE = "All"

logger = get_logger(__name__)

class AnalyticsFacade:
    """
    Centralized Analytics Service Layer.
    Aggregates functionality from specialized services into a unified interface.
    """

    def __init__(self):
        """
        Initializes the facade by orchestrating specialized internal services.
        """
        self.timeseries = TimeSeriesAnalysis()
        self.forecasting = ForecastingService()
        self.restock = RestockService()
        self.insights = InsightsService()
        self.usage = UsageIntelligence()

    def get_realtime_status(self, request=None) -> Dict[str, Any]:
        """
        Unified Real-Time Status.
        Combines current alerts, risks, and today's summary.
        """
        try:
            return self.insights.get_actionable_insights(
                days=DEFAULT_STATUS_LOOKBACK_DAYS, 
                request=request
            )
        except Exception as e:
            logger.error(f"Error fetching real-time status: {str(e)}", exc_info=True)
            return {
                "outbreaks": [], 
                "critical_stock": [], 
                "metadata": {"risk_level": "UNKNOWN"}
            }

    def get_prediction_suite(
        self, 
        drug_name: Optional[str] = None, 
        disease_name: Optional[str] = None, 
        request=None
    ) -> Dict[str, Any]:
        """
        Unified Prediction Interface.
        Provides both inventory and disease-level forecasts.
        """
        results = {}
        try:
            if drug_name:
                results['stock_depletion'] = self.forecasting.forecast_stock_depletion(
                    drug_name, 
                    request=request
                )
            
            if disease_name:
                results['disease_forecast'] = self.forecasting.forecast_all_diseases(
                    days_ahead=DEFAULT_FORECAST_HORIZON_DAYS, 
                    request=request
                )
        except Exception as e:
            logger.error(f"Error in prediction suite: {str(e)}", exc_info=True)
            
        return results

    def get_decision_support(self, request=None) -> Dict[str, Any]:
        """
        Unified Decision Support.
        Provides restock suggestions and strategic recommendations.
        """
        try:
            # Reusing insights service for recommendations
            insights_data = self.insights.get_actionable_insights(request=request)
            
            return {
                'restock': self.restock.calculate_restock_suggestions(request=request),
                'recommendations': insights_data.get('recommendations', [])
            }
        except Exception as e:
            logger.error(f"Error in decision support: {str(e)}", exc_info=True)
            return {'restock': [], 'recommendations': []}

    def get_structured_analytics(self, days: int = DEFAULT_ANALYTICS_DAYS, request=None) -> Dict[str, Any]:
        """
        Comprehensive Analytics Pipeline.
        Returns the full analytical context for the platform including trends and seasonality.
        """
        try:
            return {
                'trends': self.usage.get_all_disease_trends(days=days, request=request),
                'doctor_patterns': self.usage.get_doctor_patterns(days=days, request=request),
                'seasonality': self.timeseries.get_seasonal_patterns(
                    DEFAULT_SEASONALITY_SCOPE, 
                    request=request
                )
            }
        except Exception as e:
            logger.error(f"Error in structured analytics pipeline: {str(e)}", exc_info=True)
            return {'trends': {}, 'doctor_patterns': [], 'seasonality': {}}

# Global instance for easy access across the platform
analytics_service = AnalyticsFacade()

