"""
Insight Views - Simple Flow API
===============================
Optimized API layer for the Healthcare Analytics Platform.
Replaces the complex layered architecture with a consolidated, high-performance flow.
"""

import logging
from datetime import date
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from ..services.dashboard_service import DashboardService
from ..utils.logger import get_logger
from .utils import cache_api_response

logger = get_logger(__name__)

class AnalyticsPlatformDashboardView(APIView):
    """
    GET /api/insights/platform-dashboard/
    
    Unified Platform Dashboard.
    Provides analytics, predictions, and restock decisions in a single pass.
    
    Performance Fix:
    - Reduced database passes via Consolidated Service.
    - Payload truncation (Top 10 items).
    - Sub-second cached response.
    """
    
    @cache_api_response(timeout=300)
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            forecast_days = int(request.query_params.get('forecast_days', 8))
            
            logger.info(f"Dashboard Request: days={days}, forecast_days={forecast_days}")
            
            # Execute unified data retrieval
            dashboard_data = DashboardService.get_unified_dashboard(
                days=days, 
                forecast_days=forecast_days
            )
            
            return Response({
                'success': True,
                'data': {
                    'health_analytics': dashboard_data['analytics'],
                    'top_diseases': dashboard_data['top_diseases'],
                    'forecasts': dashboard_data['forecasts'],
                    'decisions': dashboard_data['decisions'],
                    'insights': dashboard_data.get('insights', {})
                },
                'metadata': {
                    'platform': 'Healthcare AI Platform',
                    'version': '4.1 (Tiered Architecture)',
                    'architecture': 'Multi-Layer Service coordination',
                    'generated_at': date.today().isoformat(),
                    'historical_period': f'Last {days} days',
                    'forecast_horizon': f'Next {forecast_days} days'
                }
            })
            
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': "Internal server error during dashboard generation."
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)

class InsightsSummaryView(APIView):
    """
    GET /api/insights/summary/
    
    FEATURE 9: Multi-Level Insights.
    Returns high-level decisions, outbreaks, and strategic recommendations.
    """
    
    @cache_api_response(timeout=600)
    def get(self, request):
        try:
            from ..services.insights_service import InsightsService
            days = int(request.query_params.get('days', 30))
            
            service = InsightsService()
            insights = service.get_actionable_insights(days=days)
            
            return Response({
                'success': True,
                'insights': insights
            })
        except Exception as e:
            logger.error(f"Insights error: {str(e)}")
            return Response({'error': str(e)}, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)

class UnifiedAlertView(APIView):
    """
    GET /api/insights/alerts/
    
    FEATURE 8: Unified Real-Time Alert System.
    Combines outbreaks, statistical spikes, and critical shortages.
    """
    
    @cache_api_response(timeout=60) # 1 minute cache for "near real-time" feel
    def get(self, request):
        try:
            from ..services.insights_service import InsightsService
            service = InsightsService()
            alerts = service.get_unified_alert_stream()
            
            return Response({
                'success': True,
                'count': len(alerts),
                'alerts': alerts,
                'status': 'Critical' if any(a['priority'] == 'Critical' for a in alerts) else 'Stable'
            })
        except Exception as e:
            logger.error(f"Alerts error: {str(e)}")
            return Response({'error': str(e)}, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)