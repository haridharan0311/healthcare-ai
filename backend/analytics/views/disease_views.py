from datetime import date, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response

from analytics.models import Appointment
from .utils import cache_api_response, _get_date_range, _get_db_date_range, apply_clinic_filter
from ..services.constants import ANALYTICS_CACHE_TIMEOUT, ROUNDING_PRECISION_GROWTH
from ..services.timeseries import get_seasonal_weight
from ..services.ml_engine import weighted_trend_score
from ..serializers.serializers import DiseaseTrendSerializer, CommonQuerySerializer
from ..services.aggregation import (
    aggregate_disease_counts, aggregate_daily_counts, compare_disease_trends, 
    aggregate_seasonality, get_disease_type
)
from ..services.usage import UsageIntelligence

class DiseaseTrendView(APIView):
    """
    GET /api/disease-trends/?days=30
    
    Returns high-level trends for diseases using weighted scores and seasonal adjustments.
    """
    @cache_api_response(timeout=ANALYTICS_CACHE_TIMEOUT)
    def get(self, request) -> Response:
        # Strict input validation
        query_serializer = CommonQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated_data = query_serializer.validated_data

        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)

        # Fetch aggregates for two windows to compare
        recent = aggregate_disease_counts(mid, end, queryset=appt_qs)
        older = aggregate_disease_counts(start, mid, queryset=appt_qs)

        combined = defaultdict(lambda: {
            'recent': 0, 'older': 0, 'season': 'All'
        })

        for dtype, data in recent.items():
            combined[dtype].update({
                'recent': data['count'],
                'season': data['season']
            })

        for dtype, data in older.items():
            combined[dtype]['older'] = data['count']

        if not combined:
            return Response([])

        results = []
        for dtype, data in combined.items():
            sw = get_seasonal_weight(data['season'], current_month)
            score = round(weighted_trend_score(data['recent'], data['older']) * sw, ROUNDING_PRECISION_GROWTH)
            results.append({
                'disease_name': dtype,
                'season': data['season'],
                'total_cases': data['recent'] + data['older'],
                'trend_score': score,
                'seasonal_weight': sw,
            })

        results.sort(key=lambda x: x['trend_score'], reverse=True)
        return Response(results)

class DiseaseTypeDistributionView(APIView):
    """
    GET /api/disease-trends/distribution/?days=30
    
    Distribution of diseases by type (e.g., Viral, Bacterial).
    """
    @cache_api_response(timeout=ANALYTICS_CACHE_TIMEOUT)
    def get(self, request) -> Response:
        start, end = _get_date_range(request)
        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)

        # Get raw counts grouped by disease type
        raw_counts = appt_qs.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        ).values('disease').annotate(count=Count('id'))

        type_counts = defaultdict(int)
        for entry in raw_counts:
            dtype = get_disease_type(entry['disease'])
            type_counts[dtype] += entry['count']

        total_cases = sum(type_counts.values())
        distribution = []
        for dtype, count in type_counts.items():
            distribution.append({
                'disease_type': dtype,
                'case_count': count,
                'percentage': round((count / total_cases) * 100, 2) if total_cases > 0 else 0
            })

        distribution.sort(key=lambda x: x['case_count'], reverse=True)
        return Response(distribution)

class TimeSeriesView(APIView):
    """
    GET /api/disease-trends/timeseries/?days=7&disease=Flu
    
    Provides chronological data points for disease tracking.
    """
    @cache_api_response(timeout=ANALYTICS_CACHE_TIMEOUT)
    def get(self, request) -> Response:
        start, end = _get_date_range(request)
        disease_filter = request.query_params.get('disease')

        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        daily_map_by_type = aggregate_daily_counts(start, end, disease_filter=disease_filter, queryset=appt_qs)

        results = []
        for dtype, data in daily_map_by_type.items():
            daily = data.get('daily', {}) if isinstance(data, dict) else {}
            for d, count in daily.items():
                results.append({
                    'date': d.isoformat() if hasattr(d, 'isoformat') else str(d),
                    'disease_name': dtype,
                    'case_count': count,
                })

        results.sort(key=lambda x: (x['date'], x['disease_name']))
        return Response(results)


class TrendComparisonView(APIView):
    """
    GET /api/trend-comparison/?days=7
    
    Comparative analysis between two equal time windows.
    """
    @cache_api_response(timeout=ANALYTICS_CACHE_TIMEOUT)
    def get(self, request) -> Response:
        try:
            days = int(request.query_params.get('days', 7))
        except (ValueError, TypeError):
            days = 7

        p1_start, p1_end = _get_db_date_range(days)
        p2_start = p1_start - timedelta(days=days)
        p2_end = p1_start - timedelta(days=1)

        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        results = compare_disease_trends(p2_start, p2_end, p1_start, p1_end, queryset=appt_qs)

        return Response({
            'period1': f'{p1_start} to {p1_end}',
            'period2': f'{p2_start} to {p2_end}',
            'results': results,
            'summary': {
                'increasing': sum(1 for r in results if r['direction'] == 'up'),
                'decreasing': sum(1 for r in results if r['direction'] == 'down'),
                'stable': sum(1 for r in results if r['direction'] == 'stable'),
                'new': sum(1 for r in results if r['direction'] == 'new'),
            }
        })


class SeasonalityView(APIView):
    """
    GET /api/seasonality/?days=365
    
    Aggregates diseases based on their seasonal categorization.
    """
    @cache_api_response(timeout=ANALYTICS_CACHE_TIMEOUT)
    def get(self, request) -> Response:
        start, end = _get_date_range(request)
        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        
        # Core data from service
        data = aggregate_seasonality(start, end, queryset=appt_qs)
        overall_total = appt_qs.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        ).count()

        seasons_out = {
            'Monsoon': {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
            'Summer':  {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
            'Winter':  {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
            'All':     {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
        }

        for season, sdata in data.items():
            target_season = season if season in seasons_out else 'All'
            existing = seasons_out[target_season]
            
            # Merge and sort
            merged_diseases = existing['diseases'] + sdata.get('diseases', [])
            total_cases = existing['total_cases'] + sdata.get('total_cases', 0)
            
            if merged_diseases:
                merged_diseases.sort(key=lambda x: x['case_count'], reverse=True)
                seasons_out[target_season] = {
                    'top_disease': merged_diseases[0]['disease_name'],
                    'top_disease_count': merged_diseases[0]['case_count'],
                    'total_cases': total_cases,
                    'diseases': merged_diseases
                }

        return Response({
            'period': f'{start} to {end}',
            'overall_total': overall_total,
            'seasons': seasons_out
        })


class DoctorWiseTrendsView(APIView):
    """
    GET /api/doctor-trends/?days=30&limit=10
    
    Patterns of disease diagnosis grouped by doctor.
    """
    @cache_api_response(timeout=ANALYTICS_CACHE_TIMEOUT)
    def get(self, request) -> Response:
        try:
            days = int(request.query_params.get('days', 30))
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            days, limit = 30, 10

        # Use the service layer to get standardized patterns
        service = UsageIntelligence()
        patterns = service.get_doctor_patterns(days=days, request=request)
        
        # Format for frontend compatibility
        # Frontend expects: doctor_name, disease_name (mapped from top_specialization), case_count (mapped from total_cases)
        results = []
        if isinstance(patterns, list):
            for p in patterns[:limit]:
                results.append({
                    'doctor_id': p['doctor_id'],
                    'doctor_name': p['doctor_name'],
                    'disease_name': p['top_specialization'],
                    'season': p.get('season', 'All'),
                    'case_count': p['total_cases'],
                    'efficiency_score': p['efficiency_score']
                })

        return Response({
            'period_days': days,
            'total_rows': len(results),
            'min_cases': 10, # Standard threshold for this report
            'data': results
        })
