from typing import List, Dict, Optional, Tuple, Any
from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Count, Sum, Avg, QuerySet
from django.db.models.functions import TruncDate

from analytics.models import Appointment
from inventory.models import PrescriptionLine, DrugMaster
from .aggregation import get_disease_type
from .ml_engine import (
    moving_average_forecast,
    exponential_smoothing_forecast,
    weighted_trend_score,
    predict_demand
)
from .timeseries import get_seasonal_weight
from .spike_detection import detect_spike_logic as detect_spike
from ..utils.filters import apply_clinic_filter
from ..utils.chemistry import _get_generic
from ..utils.logger import get_logger
from .constants import (
    DEFAULT_FORECAST_DAYS,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_CONFIDENCE_LEVEL,
    TREND_UP_THRESHOLD,
    TREND_DOWN_THRESHOLD,
    TREND_STRICT_UP_THRESHOLD,
    TREND_STRICT_DOWN_THRESHOLD,
    TREND_SEVERE_THRESHOLD,
    DEMAND_SAFETY_BUFFER,
    TOP_DISEASES_BATCH_LIMIT,
    REORDER_SAFETY_MULTIPLIER,
    GROWTH_RATE_RISING
)

logger = get_logger(__name__)

class ForecastingService:
    """
    Service for predictive analytics and forecasting.
    Uses historical data and machine learning techniques to predict 
    future disease cases and medicine demand.
    """
    
    def __init__(self):
        self.logger = logger
    
    def forecast_next_period(
        self,
        disease_name: str,
        days_ahead: int = DEFAULT_FORECAST_DAYS,
        confidence: float = DEFAULT_CONFIDENCE_LEVEL,
        appt_queryset: Optional[QuerySet] = None,
        request=None
    ) -> Dict[str, Any]:
        """
        Forecast disease cases for next N days.
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=DEFAULT_LOOKBACK_DAYS)
            
            if appt_queryset is None:
                appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)

            qs = (
                appt_queryset
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('appt_date')
                .annotate(day_count=Count('id'))
                .order_by('appt_date')
            )
            
            daily_counts = [row['day_count'] for row in qs]
            
            if len(daily_counts) < 3:
                return {
                    'disease': disease_name,
                    'forecast_value': 0,
                    'confidence_level': 0.0,
                    'status': 'insufficient_data',
                    'minimum_days_required': 3,
                    'days_available': len(daily_counts)
                }
            
            # Advanced: Seasonal-Trend Decomposition (Simulated via NumPy)
            import numpy as np
            import pandas as pd

            series = pd.Series(daily_counts)
            
            # 1. Trend component (Moving Average)
            trend = series.rolling(window=min(7, len(series)), min_periods=1).mean()
            
            # 2. Seasonal component (Day-of-week logic)
            # We assume a 7-day cycle for healthcare data
            if len(series) >= 14:
                seasonal_deltas = []
                for i in range(7):
                    day_indices = range(i, len(series), 7)
                    day_values = series.iloc[day_indices]
                    seasonal_deltas.append(day_values.mean() - series.mean())
                
                # Project seasonality forward
                future_seasonality = [seasonal_deltas[(len(series) + i) % 7] for i in range(days_ahead)]
            else:
                future_seasonality = [0] * days_ahead

            # 3. Forecast calculation (Trend + Seasonality)
            last_trend = trend.iloc[-1]
            slope = (trend.iloc[-1] - trend.iloc[0]) / len(trend) if len(trend) > 1 else 0
            
            forecast_points = []
            for i in range(1, days_ahead + 1):
                p = last_trend + (slope * i) + future_seasonality[i-1]
                forecast_points.append(max(0, p))

            forecast_value = sum(forecast_points) / days_ahead
            
            # Confidence intervals based on residual variance
            residuals = series - trend
            std_dev = residuals.std() if len(residuals) > 1 else (forecast_value * 0.2)
            margin = std_dev * 1.96 * (1 - (confidence - 0.9)) # Z-score for confidence
            
            return {
                'disease_name': disease_name,
                'forecast_value': round(forecast_value, 1),
                'forecast_points': [round(p, 1) for p in forecast_points],
                'confidence_level': confidence,
                'confidence_lower': round(max(0, forecast_value - margin), 1),
                'confidence_upper': round(forecast_value + margin, 1),
                'trend': 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable',
                'days_ahead': days_ahead,
                'historical_avg': round(series.mean(), 2),
                'forecast_date': (end_date + timedelta(days=days_ahead)).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Forecast failed for {disease_name}: {str(e)}", exc_info=True)
            return {'disease_name': disease_name, 'forecast_value': None, 'error': str(e)}

    def calculate_trend_score(
        self,
        disease_name: Optional[str] = None,
        recent_cases: Optional[int] = None,
        older_cases: Optional[int] = None,
        days_back: int = DEFAULT_LOOKBACK_DAYS,
        appt_queryset: Optional[QuerySet] = None
    ) -> Dict[str, Any]:
        """
        Calculate weighted trend score for disease.
        """
        try:
            if disease_name and (recent_cases is None or older_cases is None):
                end_date = date.today()
                start_date = end_date - timedelta(days=days_back)
                mid_date = start_date + (end_date - start_date) // 2
                
                if appt_queryset is None:
                    appt_queryset = Appointment.objects.all()

                recent_cases = appt_queryset.filter(
                    appointment_datetime__date__range=(mid_date, end_date),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                ).count()
                
                older_cases = appt_queryset.filter(
                    appointment_datetime__date__range=(start_date, mid_date),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                ).count()
            
            score = weighted_trend_score(recent_cases or 0, older_cases or 0)
            
            if not older_cases:
                direction = 'worsening' if recent_cases else 'stable'
                intensity = 'moderate' if recent_cases else 'none'
            else:
                ratio = (recent_cases or 0) / older_cases
                if ratio > TREND_STRICT_UP_THRESHOLD:
                    direction = 'worsening'
                    intensity = 'severe' if ratio > TREND_SEVERE_THRESHOLD else 'moderate'
                elif ratio < TREND_STRICT_DOWN_THRESHOLD:
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
                'older_cases': older_cases or 0
            }
            if disease_name: result['disease_name'] = disease_name
            return result
        except Exception as e:
            self.logger.error(f"Trend score failed: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def forecast_medicine_demand(
        self,
        drug_name: str,
        days_ahead: int = DEFAULT_LOOKBACK_DAYS,
        rx_queryset: Optional[QuerySet] = None,
        request=None
    ) -> Dict[str, Any]:
        """
        Forecast medicine demand for next N days.
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=DEFAULT_LOOKBACK_DAYS)
            
            if rx_queryset is None:
                rx_queryset = apply_clinic_filter(PrescriptionLine.objects.all(), request, clinic_field='prescription__clinic')

            qs = (
                rx_queryset
                .filter(prescription_date__range=(start_date, end_date), drug__drug_name=drug_name)
                .annotate(rx_date=TruncDate('prescription_date'))
                .values('rx_date')
                .annotate(daily_qty=Sum('quantity'))
                .order_by('rx_date')
            )
            
            daily_quantities = [row['daily_qty'] or 0 for row in qs]
            
            if not daily_quantities:
                return {'drug_name': drug_name, 'status': 'no_recent_usage', 'forecast_demand': 0}
            
            ma_val = moving_average_forecast(daily_quantities)
            es_val = exponential_smoothing_forecast(daily_quantities)
            forecast_daily = (ma_val + es_val) / 2
            forecast_total = forecast_daily * days_ahead
            
            return {
                'drug_name': drug_name,
                'days_ahead': days_ahead,
                'forecast_daily_usage': round(forecast_daily, 2),
                'forecast_total_usage': round(forecast_total, 1),
                'recommended_stock': round(forecast_total * DEMAND_SAFETY_BUFFER, 1)
            }
        except Exception as e:
            self.logger.error(f"Medicine forecast failed for {drug_name}: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def forecast_all_diseases(
        self,
        days_ahead: int = DEFAULT_FORECAST_DAYS,
        precalculated_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate forecasts for all active diseases.
        Optimized: Uses preloaded context or bulk ORM queries.
        """
        try:
            ctx = precalculated_context or {}
            limit_date = ctx.get('start_date') or (date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS))

            if 'daily_by_dtype' in ctx:
                disease_daily_map = ctx['daily_by_dtype']
            else:
                top_names_qs = (
                    Appointment.objects
                    .filter(appointment_datetime__date__gte=limit_date, disease__isnull=False, disease__is_active=True)
                    .values('disease__name')
                    .annotate(total=Count('id'))
                    .order_by('-total')[:TOP_DISEASES_BATCH_LIMIT]
                )
                top_names = [row['disease__name'] for row in top_names_qs]
                if not top_names: return []

                historical_qs = (
                    Appointment.objects
                    .filter(appointment_datetime__date__gte=limit_date, disease__name__in=top_names)
                    .annotate(day=TruncDate('appointment_datetime'))
                    .values('day', 'disease__name')
                    .annotate(count=Count('id'))
                )
                disease_daily_map = defaultdict(lambda: defaultdict(int))
                for row in historical_qs:
                    dtype = get_disease_type(row['disease__name'])
                    disease_daily_map[dtype][row['day']] += row['count']

            results = []
            for dtype, date_map in disease_daily_map.items():
                counts = [date_map.get(limit_date + timedelta(days=i), 0) for i in range(DEFAULT_LOOKBACK_DAYS + 1)]
                
                ma_val = moving_average_forecast(counts)
                es_val = exponential_smoothing_forecast(counts)
                forecast_val = (ma_val + es_val) / 2
                trend_score = weighted_trend_score(sum(counts[-7:]), sum(counts[:-7]))
                
                results.append({
                    'disease_name': dtype,
                    'forecast_value': round(forecast_val, 1),
                    'trend': 'rising' if trend_score > GROWTH_RATE_RISING else 'stable',
                    'days_ahead': days_ahead,
                    'historical_avg': round(sum(counts)/max(len(counts), 1), 1),
                    'total': sum(counts),
                    'trend_score': round(trend_score, 2)
                })
            
            return sorted(results, key=lambda x: -x['total'])[:TOP_DISEASES_BATCH_LIMIT]
        except Exception as e:
            self.logger.error(f"Bulk forecasting failed: {str(e)}", exc_info=True)
            return []

    def forecast_stock_depletion(
        self,
        drug_name: str,
        days: int = 14,
        rx_queryset: Optional[QuerySet] = None,
        request=None,
        growth_map: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        FEATURE 4: Stock Depletion Forecast.
        """
        try:
            if rx_queryset is None: rx_queryset = PrescriptionLine.objects.all()
            
            stock_data = apply_clinic_filter(DrugMaster.objects.filter(drug_name=drug_name), request).aggregate(
                total_stock=Sum('current_stock')
            )
            current_stock = stock_data['total_stock'] or 0
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            usage_sum = rx_queryset.filter(
                prescription_date__range=(start_date, end_date),
                drug__drug_name=drug_name
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            avg_daily_usage = usage_sum / max(days, 1)
            
            # Intelligence Layer: Factor in predicted future demand
            related_diseases = rx_queryset.filter(drug__drug_name=drug_name).values_list('disease__name', flat=True).distinct()
            max_growth = 0
            
            if growth_map:
                for d in related_diseases:
                    g = growth_map.get(d, 0)
                    if g > max_growth: max_growth = g
            else:
                # Late import to resolve circular dependency
                from .timeseries import TimeSeriesAnalysis
                ts = TimeSeriesAnalysis()
                for d in related_diseases:
                    growth = ts.calculate_growth_rate(d, days=7, request=request)
                    g = growth.get('growth_rate', 0)
                    if g > max_growth: max_growth = g
            
            predicted_daily_usage = avg_daily_usage * (1 + min(max_growth / 100, 1.0))
            
            if current_stock <= 0:
                days_left, status = 0, "critical"
            elif predicted_daily_usage <= 0:
                days_left, status = 999, "stable"
            else:
                days_left = current_stock / predicted_daily_usage
                status = "critical" if days_left < 7 else "low" if days_left < 14 else "sufficient"
                
            return {
                'drug_name': drug_name,
                'generic_name': _get_generic(drug_name),
                'current_stock': current_stock,
                'avg_daily_usage': round(avg_daily_usage, 2),
                'predicted_daily_usage': round(predicted_daily_usage, 2),
                'days_until_depletion': round(days_left, 1),
                'depletion_date': (date.today() + timedelta(days=int(days_left))).isoformat() if days_left < 365 else "N/A",
                'status': status,
                'recommended_reorder': round(predicted_daily_usage * 30 * REORDER_SAFETY_MULTIPLIER, 0),
                'recommendation': self._get_depletion_recommendation(status, days_left)
            }
        except Exception as e:
            self.logger.error(f"Depletion forecast failed for {drug_name}: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def _get_depletion_recommendation(self, status: str, days_left: float) -> str:
        if status == 'critical':
            return f"Action Required: Stockout expected in {round(days_left, 1)} days. Place emergency order today."
        elif status == 'low':
            return f"Order Soon: Stock will be depleted in approximately {round(days_left, 1)} days."
        return "Stock levels are currently sufficient for the projected usage."
