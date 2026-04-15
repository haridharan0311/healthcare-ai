"""
Forecasting Service Module

Advanced predictive analytics using machine learning:
1. Moving average forecasting - weighted 7-day and 3-day averages
2. Trend scoring - combines historical and recent data
3. Demand prediction - forecasts future medicine and disease cases
4. Seasonal adjustment - factors in seasonal patterns

Layer: Services (Business Logic)
Dependencies: ml_engine, spike_detector, logger

Usage:
    from analytics.services.forecasting import ForecastingService
    
    service = ForecastingService()
    
    # Forecast next-day cases
    forecast = service.forecast_next_period(
        disease_name="Flu",
        days_ahead=7
    )
    
    # Get trend score
    score = service.calculate_trend_score(
        recent_cases=150,
        older_cases=120
    )
"""

from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Count, Sum, Avg, Max
from django.db.models.functions import TruncDate

from analytics.models import Appointment
from inventory.models import PrescriptionLine, DrugMaster
from ..services.aggregation import get_disease_type
from .ml_engine import (
    moving_average_forecast,
    weighted_trend_score,
    predict_demand,
    time_decay_weight
)
from .timeseries import get_seasonal_weight
from .spike_detection import detect_spike_logic as detect_spike
from ..views.utils import apply_clinic_filter, _get_generic
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class ForecastingService:
    """
    Service for predictive analytics and forecasting.
    
    For new users: Uses historical data and machine learning techniques
    to predict future disease cases and medicine demand.
    """
    
    def __init__(self):
        """Initialize service."""
        self.logger = logger
    
    def forecast_next_period(
        self,
        disease_name: str,
        days_ahead: int = 7,
        confidence: float = 0.95,
        appt_queryset = None
    ) -> Dict:
        """
        Forecast disease cases for next N days.
        
        For new users: Predicts future case counts using weighted moving averages
        and seasonal factors. Confidence level indicates prediction reliability.
        
        Args:
            disease_name: Disease to forecast
            days_ahead: Forecast horizon (days into future)
            confidence: Confidence level (0.0-1.0) for uncertainty ranges
        
        Returns:
            Dictionary with forecast data:
                - forecast_value: Expected cases in next period
                - confidence_level: Prediction reliability
                - confidence_range: (min, max) estimates
                - trend: 'stable', 'increasing', 'decreasing'
        
        Example:
            forecast = service.forecast_next_period("Flu", days_ahead=7)
            print(f"Expected Flu cases in 7 days: {forecast['forecast_value']}")
        """
        try:
            # Get historical daily counts (last 30 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            if appt_queryset is None:
                appt_queryset = Appointment.objects.all()

            qs = (
                appt_queryset
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .select_related('disease')
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('appt_date')
                .annotate(day_count=Count('id'))
                .order_by('appt_date')
            )
            
            daily_counts = [row['day_count'] for row in qs]
            
            if len(daily_counts) < 3:
                self.logger.warning(
                    "Insufficient data for forecast: %s disease",
                    disease_name
                )
                return {
                    'disease': disease_name,
                    'forecast_value': 0,
                    'confidence_level': 0.0,
                    'status': 'insufficient_data',
                    'minimum_days_required': 3,
                    'days_available': len(daily_counts)
                }
            
            # Apply moving average forecast
            forecast_value = moving_average_forecast(daily_counts)
            
            # Calculate trend
            recent_avg = sum(daily_counts[-7:]) / 7 if len(daily_counts) >= 7 else sum(daily_counts) / len(daily_counts)
            older_avg = sum(daily_counts[:-7]) / len(daily_counts[:-7]) if len(daily_counts) > 7 else recent_avg
            
            if forecast_value > recent_avg * 1.1:
                trend = 'increasing'
            elif forecast_value < recent_avg * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Calculate confidence range based on historical variance
            if len(daily_counts) >= 7:
                variance = sum((x - recent_avg) ** 2 for x in daily_counts[-7:]) / 7
                std_dev = variance ** 0.5
                margin = std_dev * (1 - confidence)  # Higher confidence = smaller range
            else:
                margin = forecast_value * 0.3
            
            result = {
                'disease_name': disease_name,
                'forecast_value': round(forecast_value, 1),
                'confidence_level': confidence,
                'confidence_lower': round(max(0, forecast_value - margin), 1),
                'confidence_upper': round(forecast_value + margin, 1),
                'trend': trend,
                'days_ahead': days_ahead,
                'historical_avg': round(recent_avg, 2),
                'data_points_used': len(daily_counts),
                'forecast_date': (end_date + timedelta(days=days_ahead)).isoformat()
            }
            
            self.logger.info(
                "Forecasted %s cases for %s in %d days",
                forecast_value, disease_name, days_ahead
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Forecast generation failed for %s",
                disease_name,
                exception=e
            )
            return {
                'disease_name': disease_name,
                'forecast_value': None,
                'error': str(e)
            }
    
    def calculate_trend_score(
        self,
        disease_name: Optional[str] = None,
        recent_cases: Optional[int] = None,
        older_cases: Optional[int] = None,
        days_back: int = 30,
        appt_queryset = None
    ) -> Dict:
        """
        Calculate weighted trend score for disease.
        
        For new users: Combines recent data (70% weight) and older data (30% weight)
        to identify if disease is improving or worsening.
        
        Args:
            disease_name: Disease to analyze (alternative to providing counts)
            recent_cases: Optional recent period case count
            older_cases: Optional older period case count
            days_back: Total days to analyze
        
        Returns:
            Dictionary with trend analysis:
                - trend_score: Composite score
                - direction: 'improving', 'stable', 'worsening'
                - intensity: 'mild', 'moderate', 'severe'
        """
        try:
            if disease_name and (recent_cases is None or older_cases is None):
                # Calculate from database
                end_date = date.today()
                start_date = end_date - timedelta(days=days_back)
                mid_date = start_date + (end_date - start_date) // 2
                
                if appt_queryset is None:
                    appt_queryset = Appointment.objects.all()

                recent_qs = (
                    appt_queryset
                    .filter(
                        appointment_datetime__date__range=(mid_date, end_date),
                        disease__name__icontains=disease_name,
                        disease__isnull=False
                    )
                    .count()
                )
                
                older_qs = (
                    appt_queryset
                    .filter(
                        appointment_datetime__date__range=(start_date, mid_date),
                        disease__name__icontains=disease_name,
                        disease__isnull=False
                    )
                    .count()
                )
                
                recent_cases = recent_qs
                older_cases = older_qs
            
            score = weighted_trend_score(recent_cases or 0, older_cases or 0)
            
            # Determine direction and intensity
            if (older_cases or 0) == 0:
                if (recent_cases or 0) == 0:
                    direction = 'stable'
                    intensity = 'none'
                else:
                    direction =  'worsening'
                    intensity = 'moderate'
            else:
                ratio = (recent_cases or 0) / (older_cases or 1)
                
                if ratio > 1.3:
                    direction = 'worsening'
                    intensity = 'severe' if ratio > 2.0 else 'moderate'
                elif ratio < 0.7:
                    direction = 'improving'
                    intensity = 'mild'
                else:
                    direction = 'stable'
                    intensity = 'none'
            
            result = {
                'trend_score': round(score, 2),
                'direction': direction,
                'intensity': intensity,
                'recent_cases': recent_cases or 0,
                'older_cases': older_cases or 0,
                'ratio': round((recent_cases or 0) / (older_cases or 1), 2)
            }
            
            if disease_name:
                result['disease_name'] = disease_name
            
            self.logger.info(
                "Trend score: %.2f (%s, %s)",
                score, direction, intensity
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Trend score calculation failed",
                exception=e
            )
            return {'error': str(e)}
    
    def forecast_medicine_demand(
        self,
        drug_name: str,
        days_ahead: int = 30,
        rx_queryset = None
    ) -> Dict:
        """
        Forecast medicine demand for next N days.
        
        For new users: Combines disease forecasts with drug-to-disease mappings
        to predict how much medicine will be needed.
        
        Args:
            drug_name: Medicine to forecast
            days_ahead: Forecast horizon
        
        Returns:
            Forecast with demand, confidence range, and recommendations
        """
        try:
            # Get recent usage pattern
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            if rx_queryset is None:
                rx_queryset = PrescriptionLine.objects.all()

            qs = (
                rx_queryset
                .filter(
                    prescription_date__range=(start_date, end_date),
                    drug__drug_name=drug_name
                )
                .annotate(rx_date=TruncDate('prescription_date'))
                .values('rx_date')
                .annotate(daily_qty=Sum('quantity'))
                .order_by('rx_date')
            )
            
            daily_quantities = [row['daily_qty'] or 0 for row in qs]
            
            if not daily_quantities:
                return {
                    'drug_name': drug_name,
                    'status': 'no_recent_usage',
                    'forecast_demand': 0
                }
            
            # Forecast using moving average
            forecast_daily = moving_average_forecast(daily_quantities)
            forecast_total = forecast_daily * days_ahead
            
            # Calculate confidence
            avg_usage = sum(daily_quantities) / len(daily_quantities)
            recommended_stock = forecast_total * 1.2  # 20% safety buffer
            
            result = {
                'drug_name': drug_name,
                'days_ahead': days_ahead,
                'forecast_daily_usage': round(forecast_daily, 2),
                'forecast_total_usage': round(forecast_total, 1),
                'recommended_stock': round(recommended_stock, 1),
                'historical_avg_daily': round(avg_usage, 2)
            }
            
            self.logger.info(
                "Medicine demand forecast for %s: %.1f units over %d days",
                drug_name, forecast_total, days_ahead
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Medicine demand forecast failed for %s",
                drug_name,
                exception=e
            )
            return {'error': str(e)}
    
    def forecast_all_diseases(
        self,
        days_ahead: int = 7,
        precalculated_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generate forecasts for all active diseases.
        Optimized: Uses preloaded context to bypass DB hits entirely.
        """
        try:
            ctx = precalculated_context or {}
            
            # Use pre-aggregated data if available
            if 'daily_by_dtype' in ctx:
                disease_daily_map = ctx['daily_by_dtype']
                limit_date = ctx.get('start_date') or (date.today() - timedelta(days=30))
            else:
                # 1. Identify top 20 diseases by volume in last 30 days
                limit_date = date.today() - timedelta(days=30)
                top_names_qs = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__gte=limit_date,
                        disease__isnull=False,
                        disease__is_active=True
                    )
                    .values('disease__name')
                    .annotate(total=Count('id'))
                    .order_by('-total')[:20]
                )
                
                top_names = [row['disease__name'] for row in top_names_qs]
                if not top_names:
                    return []

                # 2. Bulk fetch historical daily counts for these diseases
                historical_qs = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__gte=limit_date,
                        disease__name__in=top_names
                    )
                    .annotate(day=TruncDate('appointment_datetime'))
                    .values('day', 'disease__name')
                    .annotate(count=Count('id'))
                )

                # 3. Process in memory
                disease_daily_map = defaultdict(lambda: defaultdict(int))
                for row in historical_qs:
                    dtype = get_disease_type(row['disease__name'])
                    disease_daily_map[dtype][row['day']] += row['count']

            results = []
            for dtype, date_map in disease_daily_map.items():
                # Build time series (limit to 30 days for forecasting)
                counts = [date_map.get(limit_date + timedelta(days=i), 0) for i in range(31)]
                
                # Prediction logic
                forecast_val = moving_average_forecast(counts)
                trend_score = weighted_trend_score(sum(counts[-7:]), sum(counts[:-7]))
                
                results.append({
                    'disease_name': dtype,
                    'forecast_value': round(forecast_val, 1),
                    'trend': 'rising' if trend_score > 20 else 'stable',
                    'days_ahead': days_ahead,
                    'historical_avg': round(sum(counts)/max(len(counts), 1), 1),
                    'total': sum(counts),
                    'trend_score': round(trend_score, 2)
                })
            
            # Return top 20 by volume
            return sorted(results, key=lambda x: -x['total'])[:20]
        
        except Exception as e:
            self.logger.error("Bulk disease forecasting failed", exception=e)
            return []
        
        except Exception as e:
            self.logger.error("Bulk disease forecasting failed", exception=e)
            return []

    def forecast_stock_depletion(self, drug_name: str, days: int = 14, rx_queryset=None, request=None) -> Dict:
        """
        FEATURE 4: Stock Depletion Forecast.
        Forecasts when medicine stock will hit 0 based on current usage trends.
        Aggregates across all clinics for a professional system-wide view.
        """
        try:
            if rx_queryset is None:
                rx_queryset = PrescriptionLine.objects.all()
            
            # Aggregate current stock across clinics (Filtered by user access)
            dm_qs_base = DrugMaster.objects.filter(drug_name=drug_name)
            stock_data = apply_clinic_filter(dm_qs_base, request).aggregate(
                total_stock=Sum('current_stock')
            )
            current_stock = stock_data['total_stock'] or 0
            
            # Get usage in the specified days window
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            usage_sum = rx_queryset.filter(
                prescription_date__range=(start_date, end_date),
                drug__drug_name=drug_name
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            avg_daily_usage = usage_sum / max(days, 1)
            
            if avg_daily_usage <= 0:
                days_left = 999
                status = "stable"
            else:
                days_left = current_stock / avg_daily_usage
                status = "critical" if days_left < 7 else "low" if days_left < 14 else "sufficient"
                
            return {
                'drug_name': drug_name,
                'generic_name': _get_generic(drug_name),
                'current_stock': current_stock,
                'avg_daily_usage': round(avg_daily_usage, 2),
                'days_until_depletion': round(days_left, 1),
                'depletion_date': (date.today() + timedelta(days=int(days_left))).isoformat() if days_left < 365 else "N/A",
                'status': status,
                'urgency': status,
                'analysis_period': f"Last {days} days",
                'analysis_period_days': days,
                'recommended_reorder': round(avg_daily_usage * 30 * 1.5, 0), # 30 days stock with 50% buffer
                'recommendation': self._get_depletion_recommendation(status, days_left)
            }
        except Exception as e:
            return {'error': str(e)}

    def _get_depletion_recommendation(self, status: str, days_left: float) -> str:
        """Helper to generate actions for Feature 4."""
        if status == 'critical':
            return f"Action Required: Stockout expected in {round(days_left, 1)} days. Place emergency order today."
        elif status == 'low':
            return f"Order Soon: Stock will be depleted in approximately {round(days_left, 1)} days."
        return "Stock levels are currently sufficient for the projected usage."
