"""
Insight Views - Unified API Layer for Analytics Platform

This module provides RESTful endpoints that expose the full layered architecture:
- Analytics Engine endpoints
- Prediction Engine endpoints
- Decision Engine endpoints
- Feedback Engine endpoints

For new users: These endpoints provide access to the complete analytics
platform, from raw data analysis to actionable insights and decisions.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from ..services import (
    AnalyticsEngine,
    PredictionEngine,
    DecisionEngine,
    FeedbackEngine
)
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class HealthDashboardView(APIView):
    """
    GET /api/insights/health-dashboard/
    
    Comprehensive health system dashboard combining all analytics.
    
    For new users: This is the main entry point for getting a complete
    overview of the healthcare system - disease trends, medicine usage,
    clinic performance, and key alerts.
    
    Query Parameters:
        days: Number of days to analyze (default: 30)
    """
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            engine = AnalyticsEngine()
            dashboard = engine.get_health_dashboard(days=days)
            
            return Response({
                'success': True,
                'data': dashboard,
                'metadata': {
                    'generated_at': date.today().isoformat(),
                    'analysis_period': f'Last {days} days',
                    'engine': 'AnalyticsEngine'
                }
            })
            
        except Exception as e:
            logger.error(f"Health dashboard error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiseaseTrendAnalysisView(APIView):
    """
    GET /api/insights/disease-trends/analysis/
    
    Detailed disease trend analysis with demographics and patterns.
    
    Query Parameters:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        include_demographics: Include age/gender breakdown (true/false)
    """
    def get(self, request):
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            include_demographics = request.query_params.get('include_demographics', 'false').lower() == 'true'
            
            engine = AnalyticsEngine()
            
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                analysis = engine.analyze_disease_trends(start, end, include_demographics)
            else:
                analysis = engine.analyze_disease_trends(include_demographics=include_demographics)
            
            return Response({
                'success': True,
                'data': analysis,
                'metadata': {
                    'engine': 'AnalyticsEngine',
                    'analysis_type': 'disease_trends'
                }
            })
            
        except Exception as e:
            logger.error(f"Disease trend analysis error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicineUsageAnalysisView(APIView):
    """
    GET /api/insights/medicine-usage/analysis/
    
    Comprehensive medicine usage analysis with trends and stock correlation.
    
    Query Parameters:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        include_trends: Include usage trends (true/false)
    """
    def get(self, request):
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            include_trends = request.query_params.get('include_trends', 'true').lower() == 'true'
            
            engine = AnalyticsEngine()
            
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                analysis = engine.analyze_medicine_usage(start, end, include_trends)
            else:
                analysis = engine.analyze_medicine_usage(include_trends=include_trends)
            
            return Response({
                'success': True,
                'data': analysis,
                'metadata': {
                    'engine': 'AnalyticsEngine',
                    'analysis_type': 'medicine_usage'
                }
            })
            
        except Exception as e:
            logger.error(f"Medicine usage analysis error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class DiseaseOutbreakForecastView(APIView):
    """
    GET /api/insights/predictions/disease-outbreaks/
    
    Predict potential disease outbreaks with confidence scores.
    
    For new users: This forecast identifies diseases likely to spike
    in the coming days/weeks, enabling proactive resource allocation.
    
    Query Parameters:
        days_ahead: Number of days to forecast (default: 14)
        confidence_threshold: Minimum confidence for alerts (default: 0.7)
    """
    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 14))
            confidence_threshold = float(request.query_params.get('confidence_threshold', 0.7))
            
            engine = PredictionEngine()
            forecast = engine.predict_disease_outbreaks(
                days_ahead=days_ahead,
                confidence_threshold=confidence_threshold
            )
            
            return Response({
                'success': True,
                'data': forecast,
                'metadata': {
                    'engine': 'PredictionEngine',
                    'forecast_horizon': f'Next {days_ahead} days',
                    'confidence_threshold': confidence_threshold
                }
            })
            
        except Exception as e:
            logger.error(f"Disease outbreak forecast error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicineDemandForecastView(APIView):
    """
    GET /api/insights/predictions/medicine-demand/
    
    Predict medicine demand with stock recommendations.
    
    For new users: This forecast helps ensure adequate medicine stock
    by predicting which medicines will be in high demand.
    
    Query Parameters:
        days_ahead: Number of days to forecast (default: 30)
    """
    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 30))
            
            engine = PredictionEngine()
            forecast = engine.predict_medicine_demand(days_ahead=days_ahead)
            
            return Response({
                'success': True,
                'data': forecast,
                'metadata': {
                    'engine': 'PredictionEngine',
                    'forecast_horizon': f'Next {days_ahead} days'
                }
            })
            
        except Exception as e:
            logger.error(f"Medicine demand forecast error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResourceNeedsForecastView(APIView):
    """
    GET /api/insights/predictions/resource-needs/
    
    Predict clinic resource needs (staff, rooms, supplies).
    
    Query Parameters:
        days_ahead: Number of days to forecast (default: 14)
    """
    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 14))
            
            engine = PredictionEngine()
            forecast = engine.predict_clinic_resource_needs(days_ahead=days_ahead)
            
            return Response({
                'success': True,
                'data': forecast,
                'metadata': {
                    'engine': 'PredictionEngine',
                    'forecast_horizon': f'Next {days_ahead} days'
                }
            })
            
        except Exception as e:
            logger.error(f"Resource needs forecast error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForecastDashboardView(APIView):
    """
    GET /api/insights/predictions/dashboard/
    
    Comprehensive forecasting dashboard combining all predictions.
    
    For new users: This provides a single view of all predictions -
    disease outbreaks, medicine demand, and resource needs.
    
    Query Parameters:
        days_ahead: Number of days to forecast (default: 14)
    """
    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 14))
            
            engine = PredictionEngine()
            dashboard = engine.get_forecast_dashboard(days_ahead=days_ahead)
            
            return Response({
                'success': True,
                'data': dashboard,
                'metadata': {
                    'engine': 'PredictionEngine',
                    'forecast_horizon': f'Next {days_ahead} days'
                }
            })
            
        except Exception as e:
            logger.error(f"Forecast dashboard error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class DecisionDashboardView(APIView):
    """
    GET /api/insights/decisions/dashboard/
    
    Comprehensive decision dashboard with all recommended actions.
    
    For new users: This is the main entry point for getting all
    recommended actions across all areas - restock, outbreak response,
    resource allocation, and risk mitigation.
    
    Query Parameters:
        days_ahead: Forecast horizon for decisions (default: 14)
    """
    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 14))
            
            engine = DecisionEngine()
            decisions = engine.generate_decisions(days_ahead=days_ahead)
            
            return Response({
                'success': True,
                'data': decisions,
                'metadata': {
                    'engine': 'DecisionEngine',
                    'forecast_horizon': f'Next {days_ahead} days'
                }
            })
            
        except Exception as e:
            logger.error(f"Decision dashboard error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class RestockDecisionsView(APIView):
    """
    GET /api/insights/decisions/restock/
    
    Get prioritized restock decisions with quantities and deadlines.
    """
    def get(self, request):
        try:
            engine = DecisionEngine()
            decisions = engine.make_restock_decisions()
            
            return Response({
                'success': True,
                'data': {
                    'decisions': decisions,
                    'total_decisions': len(decisions),
                    'critical_count': len([d for d in decisions if d['priority'] == 'critical']),
                    'high_priority_count': len([d for d in decisions if d['priority'] == 'high'])
                },
                'metadata': {
                    'engine': 'DecisionEngine',
                    'decision_type': 'restock'
                }
            })
            
        except Exception as e:
            logger.error(f"Restock decisions error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class OutbreakResponseDecisionsView(APIView):
    """
    GET /api/insights/decisions/outbreak-response/
    
    Get disease outbreak response decisions with specific actions.
    """
    def get(self, request):
        try:
            engine = DecisionEngine()
            decisions = engine.make_outbreak_response_decisions()
            
            return Response({
                'success': True,
                'data': {
                    'decisions': decisions,
                    'total_decisions': len(decisions),
                    'critical_count': len([d for d in decisions if d['priority'] == 'critical']),
                    'high_priority_count': len([d for d in decisions if d['priority'] == 'high'])
                },
                'metadata': {
                    'engine': 'DecisionEngine',
                    'decision_type': 'outbreak_response'
                }
            })
            
        except Exception as e:
            logger.error(f"Outbreak response decisions error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResourceAllocationDecisionsView(APIView):
    """
    GET /api/insights/decisions/resource-allocation/
    
    Get resource allocation decisions for clinics.
    """
    def get(self, request):
        try:
            engine = DecisionEngine()
            decisions = engine.make_resource_allocation_decisions()
            
            return Response({
                'success': True,
                'data': {
                    'decisions': decisions,
                    'total_decisions': len(decisions),
                    'high_priority_count': len([d for d in decisions if d['priority'] == 'high'])
                },
                'metadata': {
                    'engine': 'DecisionEngine',
                    'decision_type': 'resource_allocation'
                }
            })
            
        except Exception as e:
            logger.error(f"Resource allocation decisions error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class RiskMitigationDecisionsView(APIView):
    """
    GET /api/insights/decisions/risk-mitigation/
    
    Get risk mitigation decisions with preventive actions.
    """
    def get(self, request):
        try:
            engine = DecisionEngine()
            decisions = engine.make_risk_mitigation_decisions()
            
            return Response({
                'success': True,
                'data': {
                    'decisions': decisions,
                    'total_decisions': len(decisions),
                    'by_risk_type': {
                        'stock_out': len([d for d in decisions if d.get('risk_type') == 'stock_out']),
                        'surveillance_gap': len([d for d in decisions if d.get('risk_type') == 'surveillance_gap']),
                        'resource_constraint': len([d for d in decisions if d.get('risk_type') == 'resource_constraint']),
                        'quality_issue': len([d for d in decisions if d.get('risk_type') == 'quality_issue'])
                    }
                },
                'metadata': {
                    'engine': 'DecisionEngine',
                    'decision_type': 'risk_mitigation'
                }
            })
            
        except Exception as e:
            logger.error(f"Risk mitigation decisions error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDBACK ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionAccuracyView(APIView):
    """
    GET /api/insights/feedback/prediction-accuracy/
    
    Track and analyze prediction accuracy over time.
    
    For new users: This shows how accurate past predictions were,
    helping to understand system reliability and identify improvements.
    
    Query Parameters:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    def get(self, request):
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            engine = FeedbackEngine()
            
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                accuracy = engine.track_prediction_accuracy(start, end)
            else:
                accuracy = engine.track_prediction_accuracy()
            
            return Response({
                'success': True,
                'data': accuracy,
                'metadata': {
                    'engine': 'FeedbackEngine',
                    'analysis_type': 'prediction_accuracy'
                }
            })
            
        except Exception as e:
            logger.error(f"Prediction accuracy error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class DecisionOutcomesView(APIView):
    """
    GET /api/insights/feedback/decision-outcomes/
    
    Monitor the effectiveness of past decisions.
    
    Query Parameters:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    def get(self, request):
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            engine = FeedbackEngine()
            
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                outcomes = engine.monitor_decision_outcomes(start, end)
            else:
                outcomes = engine.monitor_decision_outcomes()
            
            return Response({
                'success': True,
                'data': outcomes,
                'metadata': {
                    'engine': 'FeedbackEngine',
                    'analysis_type': 'decision_outcomes'
                }
            })
            
        except Exception as e:
            logger.error(f"Decision outcomes error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImprovementRecommendationsView(APIView):
    """
    GET /api/insights/feedback/improvement-recommendations/
    
    Get system improvement recommendations based on feedback analysis.
    
    For new users: This provides actionable recommendations for
    improving the entire analytics system based on performance data.
    """
    def get(self, request):
        try:
            engine = FeedbackEngine()
            recommendations = engine.get_improvement_recommendations()
            
            return Response({
                'success': True,
                'data': recommendations,
                'metadata': {
                    'engine': 'FeedbackEngine',
                    'analysis_type': 'improvement_recommendations'
                }
            })
            
        except Exception as e:
            logger.error(f"Improvement recommendations error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED PLATFORM ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyticsPlatformDashboardView(APIView):
    """
    GET /api/insights/platform-dashboard/
    
    Complete analytics platform dashboard combining all engines.
    
    For new users: This is the ultimate single endpoint that provides
    everything - analytics, predictions, decisions, and feedback in
    one comprehensive response.
    
    Query Parameters:
        days: Number of historical days to analyze (default: 30)
        forecast_days: Number of days to forecast (default: 14)
    """
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            forecast_days = int(request.query_params.get('forecast_days', 14))
            
            # Initialize all engines
            analytics_engine = AnalyticsEngine()
            prediction_engine = PredictionEngine()
            decision_engine = DecisionEngine()
            feedback_engine = FeedbackEngine()
            
            # Get data from all engines
            health_dashboard = analytics_engine.get_health_dashboard(days=days)
            forecast_dashboard = prediction_engine.get_forecast_dashboard(days_ahead=forecast_days)
            decisions = decision_engine.generate_decisions(days_ahead=forecast_days)
            recommendations = feedback_engine.get_improvement_recommendations()
            
            return Response({
                'success': True,
                'data': {
                    'health_analytics': health_dashboard,
                    'forecasts': forecast_dashboard,
                    'decisions': decisions,
                    'feedback': recommendations
                },
                'metadata': {
                    'platform': 'Healthcare Analytics Platform',
                    'version': '2.0',
                    'architecture': 'Layered (Analytics → Prediction → Decision → Feedback)',
                    'generated_at': date.today().isoformat(),
                    'historical_period': f'Last {days} days',
                    'forecast_horizon': f'Next {forecast_days} days',
                    'engines': {
                        'analytics': 'AnalyticsEngine',
                        'prediction': 'PredictionEngine',
                        'decision': 'DecisionEngine',
                        'feedback': 'FeedbackEngine'
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Platform dashboard error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)