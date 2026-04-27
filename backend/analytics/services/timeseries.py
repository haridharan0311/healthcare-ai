"""
Layer 2: Analytics - Time Series Analysis Module

Provides logic for interpreting temporal patterns in healthcare data:
1. Disease Growth Rate - Calculates % change over time windows.
2. Seasonal Intelligence - Automatically analyzes trends based on seasons.
3. Temporal Pattern Mapping - Identifies daily/weekly usage cycles.
"""

from datetime import timedelta
from typing import Dict, List
from collections import defaultdict

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from analytics.models import Appointment, Disease
from .aggregation import get_disease_type
from ..utils.filters import apply_clinic_filter
from ..utils.logger import get_logger

# Shared Constants (I will move these to a central file in the next step)
DEFAULT_GROWTH_WINDOW_DAYS = 7
DEFAULT_DAILY_TREND_DAYS = 30
PATTERN_CONFIDENCE_THRESHOLD = 100

# Trend thresholds (Centralized)
GROWTH_RATE_RISING = 20
GROWTH_RATE_INCREASING = 5
GROWTH_RATE_DECREASING = -5

# Seasonal Configuration
SEASON_MONTHS = {
    "Summer":  [3, 4, 5, 6],
    "Monsoon": [7, 8, 9, 10],
    "Winter":  [11, 12, 1, 2],
}
SEASON_WEIGHT_ACTIVE = 1.5
SEASON_WEIGHT_DEFAULT = 1.0

logger = get_logger(__name__)

def get_seasonal_weight(season: str, current_month: int) -> float:
    """Helper for seasonal weight calculation based on current month."""
    in_season_months = SEASON_MONTHS.get(season, [])
    return SEASON_WEIGHT_ACTIVE if current_month in in_season_months else SEASON_WEIGHT_DEFAULT

class TimeSeriesAnalysis:
    """Service for time-series and trend interpretation."""
    
    def __init__(self):
        pass

    def _get_trend_status(self, growth_rate: float, cases: int) -> str:
        """Internal helper to classify trend status based on growth rate."""
        if cases == 0 and growth_rate > 0:
            return 'new'
        if growth_rate > GROWTH_RATE_RISING:
            return 'rising'
        if growth_rate > GROWTH_RATE_INCREASING:
            return 'increasing'
        if growth_rate < GROWTH_RATE_DECREASING:
            return 'decreasing'
        return 'stable'

    def calculate_growth_rate(
        self,
        disease_name: str,
        days: int = DEFAULT_GROWTH_WINDOW_DAYS,
        appt_queryset = None,
        request = None
    ) -> Dict:
        """
        FEATURE 1: Disease Growth Rate Indicator.
        Calculates percentage change between two time windows.
        """
        try:
            end_date = timezone.now().date()
            recent_start = end_date - timedelta(days=days)
            prev_end = recent_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days)

            if appt_queryset is None:
                appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)

            base_qs = appt_queryset.filter(
                disease__name__icontains=disease_name,
                disease__isnull=False
            )

            recent_count = base_qs.filter(
                appointment_datetime__date__range=(recent_start, end_date)
            ).count()

            previous_count = base_qs.filter(
                appointment_datetime__date__range=(prev_start, prev_end)
            ).count()

            if previous_count == 0:
                growth_rate = 100.0 if recent_count > 0 else 0.0
            else:
                growth_rate = ((recent_count - previous_count) / previous_count) * 100

            status = self._get_trend_status(growth_rate, recent_count)

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
            logger.error(f"Growth rate calculation failed for {disease_name}: {str(e)}", exc_info=True)
            return {'error': 'Failed to calculate growth rate.'}

    def calculate_bulk_growth_rates(
        self, 
        days: int = DEFAULT_GROWTH_WINDOW_DAYS, 
        appt_queryset=None,
        request=None
    ) -> Dict[str, float]:
        """
        FEATURE 1, 8: Bulk Growth Rate Calculation.
        Calculates percentage change for all diseases in two time windows using optimized DB passes.
        """
        try:
            end_date = timezone.now().date()
            recent_start = end_date - timedelta(days=days)
            prev_end = recent_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days)

            if appt_queryset is None:
                appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)

            # 1. Get counts for Recent period
            recent_qs = (
                appt_queryset
                .filter(appointment_datetime__date__range=(recent_start, end_date), disease__isnull=False)
                .values('disease__name')
                .annotate(count=Count('id'))
            )
            recent_counts = defaultdict(int)
            for row in recent_qs:
                dtype = get_disease_type(row['disease__name'])
                recent_counts[dtype] += row['count']

            # 2. Get counts for Previous period
            prev_qs = (
                appt_queryset
                .filter(appointment_datetime__date__range=(prev_start, prev_end), disease__isnull=False)
                .values('disease__name')
                .annotate(count=Count('id'))
            )
            prev_counts = defaultdict(int)
            for row in prev_qs:
                dtype = get_disease_type(row['disease__name'])
                prev_counts[dtype] += row['count']

            # 3. Calculate rates
            growth_map = {}
            all_types = set(recent_counts.keys()) | set(prev_counts.keys())
            for dtype in all_types:
                r = recent_counts.get(dtype, 0)
                p = prev_counts.get(dtype, 0)
                if p == 0:
                    growth_map[dtype] = 100.0 if r > 0 else 0.0
                else:
                    growth_map[dtype] = round(((r - p) / p) * 100, 2)
            
            return growth_map
        except Exception as e:
            logger.error(f"Bulk growth calculation failed: {str(e)}", exc_info=True)
            return {}

    def get_seasonal_patterns(self, disease_name: str, appt_queryset=None, request=None) -> Dict:
        """
        FEATURE 6: Seasonal Intelligence Engine.
        Analyzes disease trends based on seasons and learns shifts in patterns.
        """
        if appt_queryset is None:
            appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)
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
            
            # Optimized fetch for historical season
            disease_record = Disease.objects.filter(name__icontains=disease_name).first()
            historical_season = disease_record.season if disease_record else "Unknown"
            
            # 3. Detect shifts (Learning component)
            shift_detected = current_peak != historical_season and historical_season != "All"
            
            confidence = round(min(total / PATTERN_CONFIDENCE_THRESHOLD, 1.0), 2) if total > 0 else 0

            return {
                'disease_name': disease_name,
                'seasonal_distribution': patterns,
                'total_recorded_cases': total,
                'current_peak_season': current_peak,
                'historical_peak_season': historical_season,
                'pattern_shift_detected': shift_detected,
                'confidence_score': confidence,
                'status': 'pattern_shifted' if shift_detected else 'consistent_with_history'
            }
        except Exception as e:
            logger.error(f"Seasonal analysis failed for {disease_name}: {str(e)}", exc_info=True)
            return {'error': 'Failed to analyze seasonal patterns.'}

    def get_daily_trends(self, disease_name: str, days: int = DEFAULT_DAILY_TREND_DAYS, appt_queryset=None, request=None) -> List[Dict]:
        """Expose daily time-series data for a specific disease."""
        if appt_queryset is None:
            appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)
            
        try:
            start_date = timezone.now().date() - timedelta(days=days)
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
        except Exception as e:
            logger.error(f"Daily trend retrieval failed for {disease_name}: {str(e)}", exc_info=True)
            return []

