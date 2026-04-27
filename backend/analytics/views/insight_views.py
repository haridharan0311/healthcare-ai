"""
Insight Views - Simple Flow API
===============================
Optimized API layer for the Healthcare Analytics Platform.
Replaces the complex layered architecture with a consolidated, high-performance flow.
"""

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from ..services.analytics_facade import analytics_service
from ..utils.logger import get_logger
from .utils import cache_api_response

# Internal Constants for Analytics Views
# Note: In a larger project, these should be moved to settings.py or a dedicated constants.py
DEFAULT_ANALYTICS_DAYS = 30
DASHBOARD_CACHE_TIMEOUT = 300
ALERTS_CACHE_TIMEOUT = 60
PLATFORM_METADATA = {
    'platform': 'Healthcare AI Platform',
    'service_layer': 'AnalyticsFacade',
}

logger = get_logger(__name__)

class AnalyticsPlatformDashboardView(APIView):
    """
    GET /api/insights/platform-dashboard/
    
    Unified Platform Dashboard via Centralized Analytics Facade.
    """
    
    @cache_api_response(timeout=DASHBOARD_CACHE_TIMEOUT)
    def get(self, request):
        """
        Retrieves structured analytics and decision support data for the dashboard.
        """
        try:
            # Safely parse the 'days' parameter
            try:
                days_param = request.query_params.get('days', DEFAULT_ANALYTICS_DAYS)
                days = int(days_param)
            except (ValueError, TypeError):
                days = DEFAULT_ANALYTICS_DAYS
                logger.warning(f"Invalid 'days' parameter: {days_param}. Defaulting to {DEFAULT_ANALYTICS_DAYS}.")

            logger.info(f"Dashboard Request via Facade: days={days}")
            
            # Fetch data from the centralized analytical facade
            pipeline_data = analytics_service.get_structured_analytics(days=days, request=request)
            decision_data = analytics_service.get_decision_support(request=request)
            
            # Construct a structured response
            response_data = {
                'success': True,
                'data': {
                    'trends': pipeline_data.get('trends'),
                    'health_analytics': pipeline_data.get('trends'),
                    'decisions': decision_data.get('restock'),
                    'recommendations': decision_data.get('recommendations'),
                    'doctor_patterns': pipeline_data.get('doctor_patterns')
                },
                'metadata': {
                    **PLATFORM_METADATA,
                    'generated_at': timezone.now().date().isoformat()
                }
            }
            return Response(response_data, status=drf_status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Dashboard processing error: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False, 
                    'error': 'An unexpected error occurred while generating dashboard insights.'
                },
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InsightsSummaryView(APIView):
    """
    GET /api/insights/summary/
    
    High-level platform summary and status metrics.
    """
    
    @cache_api_response(timeout=DASHBOARD_CACHE_TIMEOUT)
    def get(self, request):
        try:
            # Fetch unified status info from the facade
            status_info = analytics_service.get_realtime_status(request=request)
            
            summary = {
                'outbreak_count': len(status_info.get('outbreaks', [])),
                'rising_threats': len(status_info.get('rising_trends', [])),
                'stock_alerts': len(status_info.get('critical_stock', [])),
                'risk_level': status_info.get('metadata', {}).get('risk_level', 'LOW'),
                'recommendations': status_info.get('recommendations', [])[:3]
            }
            
            return Response({
                'success': True,
                'summary': summary,
                'generated_at': timezone.now().isoformat()
            }, status=drf_status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Summary retrieval error: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False, 
                    'error': 'An unexpected error occurred while generating insight summary.'
                },
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UnifiedAlertView(APIView):
    """
    GET /api/insights/alerts/
    
    Unified Real-Time Alert System via Centralized Analytics Facade.
    """
    
    @cache_api_response(timeout=ALERTS_CACHE_TIMEOUT)
    def get(self, request):
        """
        Retrieves real-time system alerts and current risk levels.
        """
        try:
            # Fetch unified status info from the facade
            status_info = analytics_service.get_realtime_status(request=request)
            
            # Consolidate different alert types
            outbreaks = status_info.get('outbreaks', [])
            critical_stock = status_info.get('critical_stock', [])
            alerts = outbreaks + critical_stock
            
            # Extract risk level metadata safely
            risk_metadata = status_info.get('metadata', {})
            risk_level = risk_metadata.get('risk_level', 'LOW')
            
            return Response({
                'success': True,
                'count': len(alerts),
                'alerts': alerts,
                'risk_level': risk_level
            }, status=drf_status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Alerts retrieval error: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False, 
                    'error': 'An unexpected error occurred while fetching real-time alerts.'
                },
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
