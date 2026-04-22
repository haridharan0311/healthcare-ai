"""
Layer 2: Analytics - Time Series Analysis Module

Provides logic for interpreting temporal patterns in healthcare data:
1. Disease Growth Rate - Calculates % change over time windows.
2. Seasonal Intelligence - Automatically analyzes trends based on seasons.
3. Temporal Pattern Mapping - Identifies daily/weekly usage cycles.

Usage:
    from analytics.services.timeseries import TimeSeriesAnalysis
    
    analysis = TimeSeriesAnalysis()
    growth = analysis.calculate_growth_rate("Flu", days=7)
    seasonal = analysis.get_seasonal_patterns("Malaria")
"""

from datetime import date, timedelta
from typing import Dict, List, Optional
from django.db.models import Count
from django.db.models.functions import TruncDate

from analytics.models import Appointment
from .aggregation import get_disease_type
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

def get_seasonal_weight(season: str, current_month: int) -> float:
    """Helper for seasonal weight calculation."""
    season_months = {
        "Summer":  [3, 4, 5, 6],
        "Monsoon": [7, 8, 9, 10],
        "Winter":  [11, 12, 1, 2],
    }
    in_season_months = season_months.get(season, [])
    return 1.5 if current_month in in_season_months else 1.0

logger = get_logger(__name__)

class TimeSeriesAnalysis:
    """Service for time-series and trend interpretation."""
    
    def __init__(self):
        self.logger = logger

    def calculate_growth_rate(
        self,
        disease_name: str,
        days: int = 7,
        appt_queryset = None
    ) -> Dict:
        """
        FEATURE 1: Disease Growth Rate Indicator.
        Calculates percentage change between two time windows.
        """
        try:
            end_date = date.today()
            recent_start = end_date - timedelta(days=days)
            prev_end = recent_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days)

            if appt_queryset is None:
                appt_queryset = Appointment.objects.all()

            # Using aggregation for speed instead of .count() if possible
            recent_count = (
                appt_queryset
                .filter(
                    appointment_datetime__date__range=(recent_start, end_date),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .count()
            )

            previous_count = (
                appt_queryset
                .filter(
                    appointment_datetime__date__range=(prev_start, prev_end),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .count()
            )

            if previous_count == 0:
                growth_rate = 100.0 if recent_count > 0 else 0.0
                status = 'new' if recent_count > 0 else 'stable'
            else:
                growth_rate = ((recent_count - previous_count) / previous_count) * 100
                status = 'rising' if growth_rate > 20 else 'increasing' if growth_rate > 5 else 'decreasing' if growth_rate < -5 else 'stable'

            return {
                'disease_name': disease_name,
                'growth_rate': round(growth_rate, 2),
                'recent_cases': recent_count,
                'previous_cases': previous_count,
                'period_days': days,
                'status': status,
                'direction': 'up' if growth_rate > 0 else 'down' if growth_rate < 0 else 'none',
                'change_magnitude': abs(recent_count - previous_count)
            }
        except Exception as e:
            self.logger.error(f"Growth rate calculation failed: {str(e)}")
            return {'error': str(e)}

    def get_seasonal_patterns(self, disease_name: str, appt_queryset=None) -> Dict:
        """
        FEATURE 6: Seasonal Intelligence Engine.
        Analyzes disease trends based on seasons and learns shifts in patterns.
        """
        if appt_queryset is None:
            appt_queryset = Appointment.objects.all()
        try:
            # 1. Query current distributions
            qs = (
                appt_queryset
                .filter(disease__name__icontains=disease_name, disease__isnull=False)
                .select_related('disease')
                .values('disease__season')
                .annotate(cases=Count('id'))
            )
            
            patterns = {row['disease__season'] or 'Unknown': row['cases'] for row in qs}
            total = sum(patterns.values())
            
            # 2. Identify peak and compare with historical
            current_peak = max(patterns, key=patterns.get) if patterns else "Unknown"
            
            # Fetch historical from first matching record
            from analytics.models import Disease
            historical_season = Disease.objects.filter(name__icontains=disease_name).first().season if Disease.objects.filter(name__icontains=disease_name).exists() else "Unknown"
            
            # 3. Detect shifts (Learning component)
            shift_detected = current_peak != historical_season and historical_season != "All"
            
            return {
                'disease_name': disease_name,
                'seasonal_distribution': patterns,
                'total_recorded_cases': total,
                'current_peak_season': current_peak,
                'historical_peak_season': historical_season,
                'pattern_shift_detected': shift_detected,
                'confidence_score': round(min(total / 100, 1.0), 2) if total > 0 else 0,
                'status': 'pattern_shifted' if shift_detected else 'consistent_with_history'
            }
        except Exception as e:
            self.logger.error(f"Seasonal analysis failed: {str(e)}")
            return {'error': str(e)}

    def get_daily_trends(self, disease_name: str, days: int = 30, appt_queryset=None) -> List[Dict]:
        """Expose daily time-series data."""
        if appt_queryset is None:
            appt_queryset = Appointment.objects.all()
        start_date = date.today() - timedelta(days=days)
        qs = (
            appt_queryset
            .filter(
                appointment_datetime__date__gte=start_date,
                disease__name__icontains=disease_name,
                disease__isnull=False
            )
            .annotate(day=TruncDate('appointment_datetime'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        return [{'date': str(row['day']), 'count': row['count']} for row in qs]
