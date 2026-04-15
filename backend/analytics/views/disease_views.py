import csv
import re
from datetime import date, timedelta
from collections import defaultdict

from django.http import HttpResponse
from django.db.models import Count, Avg, Max, Sum, Min, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from django.core.cache import cache

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic

from ..services.ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from ..services.timeseries import get_seasonal_weight
from ..services.spike_detection import detect_spike_logic as detect_spike
from ..serializers.serializers import (
    DiseaseTrendSerializer, TimeSeriesPointSerializer,
    SpikeAlertSerializer, RestockSuggestionSerializer
)
from ..services.restock_service import RestockService
from ..utils.validators import validate_positive_int

from ..services.aggregation import (
    aggregate_disease_counts, aggregate_daily_counts, build_daily_list,
    aggregate_medicine_usage, compare_disease_trends, aggregate_top_medicines,
    aggregate_seasonality, aggregate_doctor_wise,
    aggregate_weekly, aggregate_monthly, get_disease_type,
)

from .utils import (
    cache_api_response, GENERIC_MAP, _get_generic, _extract_district,
    _get_db_date_range, _get_date_range, _build_daily_list, apply_clinic_filter
)

# disease_views.py extracted classes

class DiseaseTrendView(APIView):
    """
    GET /api/disease-trends/?days=30

    1.1 Disease Aggregation — Count cases per disease using ORM Count.
    No Python loops for aggregation. Uses select_related for performance.
    Supports date filtering via ?days= param.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        appt_qs_base = Appointment.objects.all()
        appt_qs = apply_clinic_filter(appt_qs_base, request)

        def get_filtered_aggregates(date_start, date_end):
            return aggregate_disease_counts(date_start, date_end, queryset=appt_qs)

        recent = get_filtered_aggregates(mid, end)
        older = get_filtered_aggregates(start, mid)

        combined = defaultdict(lambda: {
            'recent': 0, 'older': 0, 'season': 'All', 'category': '', 'severity': 1
        })

        for dtype, data in recent.items():
            combined[dtype].update({
                'recent': data['count'],
                'season': data['season'],
                'category': data['category'],
                'severity': data['severity']
            })

        for dtype, data in older.items():
            combined[dtype]['older'] = data['count']

        if not combined:
            return Response([])

        results = []
        for dtype, data in combined.items():
            sw = get_seasonal_weight(data['season'], current_month)
            score = round(weighted_trend_score(data['recent'], data['older']) * sw, 2)
            results.append({
                'disease_name': dtype,
                'season': data['season'],
                'total_cases': data['recent'] + data['older'],
                'trend_score': score,
                'seasonal_weight': sw,
            })

        results.sort(key=lambda x: x['trend_score'], reverse=True)
        return Response(results)


# ─── 1.2 Time-Series Aggregation → Time-Series API ───────────────────────────



class TimeSeriesView(APIView):
    """
    GET /api/disease-trends/timeseries/?days=7&disease=Flu

    1.2 Time-Series Aggregation — Group by date using TruncDate.
    Groups by disease. Supports last 7 / 30 days via ?days= param.
    Uses ORM aggregation — no Python loops.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        start, end = _get_date_range(request)
        disease_filter = request.query_params.get('disease')

        appt_qs_base = Appointment.objects.all()
        appt_qs = apply_clinic_filter(appt_qs_base, request)

        # 1. Daily counts per disease (ORM TruncDate) using aggregated service
        daily_map_by_type = aggregate_daily_counts(start, end, disease_filter=disease_filter, queryset=appt_qs)

        results = []
        for dtype, data in daily_map_by_type.items():
            daily = data.get('daily', {})
            for d, count in daily.items():
                results.append({
                    'date': d.isoformat() if hasattr(d, 'isoformat') else str(d),
                    'disease_name': dtype,
                    'case_count': count,
                })

        results.sort(key=lambda x: (x['date'], x['disease_name']))
        return Response(results)


# ─── 1.3 Medicine Usage Aggregation → Medicine Usage API ─────────────────────



class TrendComparisonView(APIView):
    """
    GET /api/trend-comparison/?days=7

    Compares this period vs previous period of same length.
    Returns increase/decrease % per disease.
    Example: days=7 → this week vs last week.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 7))
        except ValueError:
            days = 7

        p1_start, p1_end = _get_db_date_range(days)
        p2_start, p2_end = _get_db_date_range(days * 2) # Overlap as per logic
        # Overwriting for precise comparison logic
        p2_start = p2_end - timedelta(days=days*2)
        p2_end   = p1_start - timedelta(days=1)

        appt_qs_base = Appointment.objects.all()
        appt_qs = apply_clinic_filter(appt_qs_base, request)

        results = compare_disease_trends(p2_start, p2_end, p1_start, p1_end, queryset=appt_qs)

        if not results:
            return Response({
                'period1': f'{p1_start} to {p1_end}',
                'period2': f'{p2_start} to {p2_end}',
                'results': [],
                'summary': {'increasing': 0, 'decreasing': 0, 'stable': 0, 'new': 0}
            })

        return Response({
            'period1':  f'{p1_start} to {p1_end}',
            'period2':  f'{p2_start} to {p2_end}',
            'results':  results,
            'summary': {
                'increasing': sum(1 for r in results if r['direction'] == 'up'),
                'decreasing': sum(1 for r in results if r['direction'] == 'down'),
                'stable':     sum(1 for r in results if r['direction'] == 'stable'),
                'new':        sum(1 for r in results if r['direction'] == 'new'),
            }
        })


# ── New Feature 2: Top Medicines Dashboard ────────────────────────────────────



class SeasonalityView(APIView):
    """
    GET /api/seasonality/?days=365

    Groups disease cases by season (Summer/Monsoon/Winter/All).
    The "All" section = only diseases whose season field = "All".
    Monsoon + Summer + Winter cases are separate — they do NOT add up to "All".
    "All" means diseases active in all seasons (e.g. Hypertension).
    Total across all seasons will exceed total appointments because one
    appointment may be counted in its specific season bucket only.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end = _get_date_range(request)
        
        appt_qs_base = Appointment.objects.all()
        appt_qs = apply_clinic_filter(appt_qs_base, request)

        # Use new refactored service for seasonality
        data = aggregate_seasonality(start, end, queryset=appt_qs)

        # Overall total = sum of all appointments in range (already filtered)
        overall_total = appt_qs.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        ).count()

        # Adapt service output to legacy view format
        seasons_out = {
            'Monsoon': {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
            'Summer':  {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
            'Winter':  {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
            'All':     {'top_disease': None, 'top_disease_count': 0, 'total_cases': 0, 'diseases': []},
        }
        for season, sdata in data.items():
            total = sdata['total_cases']
            seasons_out[season] = {
                'top_disease':       sdata['top_disease'],
                'top_disease_count': sdata['top_disease_count'],
                'total_cases':       total,
                'diseases': [
                    {
                        'disease_name': d['disease_name'],
                        'case_count':   d['case_count'],
                        'percentage':   round(d['case_count'] / total * 100, 1) if total > 0 else 0,
                    }
                    for d in sdata['diseases']
                ],
            }

        return Response({
            'period':        f'{start} to {end}',
            'overall_total': overall_total,
            'note':          'Seasons are independent groups based on Disease.season field. '
                             '"All" = diseases active year-round. Totals per season do not sum to overall_total.',
            'seasons':       seasons_out,
        })


# ─── Doctor-wise Trends ───────────────────────────────────────────────────────



class DoctorWiseTrendsView(APIView):
    """
    GET /api/doctor-trends/?days=30&min_cases=10

    Groups by doctor + disease type.
    Only returns rows where case_count >= min_cases (default 10).
    Respects ?days= date range.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end = _get_date_range(request)
        try:
            min_cases = int(request.query_params.get('min_cases', 1))
            limit     = int(request.query_params.get('limit', 3))
        except ValueError:
            min_cases = 1
            limit     = 3

        # Pure ORM aggregation — group by doctor + disease
        qs_base = Appointment.objects.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        qs = (
            apply_clinic_filter(qs_base, request)
            .select_related('doctor', 'disease')
            .values(
                'doctor__id',
                'doctor__first_name',
                'doctor__last_name',
                'disease__name',
                'disease__season',
            )
            .annotate(case_count=Count('id'))
            .filter(case_count__gte=min_cases)   # Lower threshold
            .order_by('-case_count')[:limit]      # Limit output items
        )

        results = [
            {
                'doctor_id':    row['doctor__id'],
                'doctor_name':  f"{row['doctor__first_name']} {row['doctor__last_name'] or ''}".strip(),
                'disease_name': get_disease_type(row['disease__name']),
                'season':       row['disease__season'],
                'case_count':   row['case_count'],
            }
            for row in qs
        ]

        return Response({
            'period':     f'{start} to {end}',
            'min_cases':  min_cases,
            'limit':      limit,
            'total_rows': len(results),
            'data':       results,
        })


# ─── Weekly Report ────────────────────────────────────────────────────────────



