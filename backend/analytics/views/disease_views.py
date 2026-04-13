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
    _get_db_date_range, _get_date_range, _build_daily_list
)

# disease_views.py extracted classes

class DiseaseTrendView(APIView):
    """
    GET /api/disease-trends/?days=30

    1.1 Disease Aggregation — Count cases per disease using ORM Count.
    No Python loops for aggregation. Uses select_related for performance.
    Supports date filtering via ?days= param.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end    = _get_date_range(request)
        current_month = date.today().month
        mid           = end - timedelta(days=7)

        # ORM aggregation — recent window (last 7 days)
        recent_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(mid, end),
                disease__isnull=False,
                disease__is_active=True,
            )
            .select_related('disease')
            .values('disease__name', 'disease__season',
                    'disease__category', 'disease__severity')
            .annotate(recent_count=Count('id'))
        )

        # ORM aggregation — older window
        older_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, mid),
                disease__isnull=False,
                disease__is_active=True,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(older_count=Count('id'))
        )

        older_map = {
            get_disease_type(r['disease__name']): r['older_count']
            for r in older_qs
        }

        # Build result — no loops for DB aggregation
        type_data = defaultdict(lambda: {
            'season': 'All', 'category': '', 'severity': 1,
            'recent': 0, 'older': 0
        })

        for row in recent_qs:
            dtype = get_disease_type(row['disease__name'])
            type_data[dtype]['season']   = row['disease__season']
            type_data[dtype]['category'] = row['disease__category'] or ''
            type_data[dtype]['severity'] = row['disease__severity']
            type_data[dtype]['recent']  += row['recent_count']
            type_data[dtype]['older']   += older_map.get(dtype, 0)

        if not type_data:
            return Response([])

        results = []
        for dtype, data in type_data.items():
            sw    = get_seasonal_weight(data['season'], current_month)
            score = round(
                weighted_trend_score(data['recent'], data['older']) * sw, 2
            )
            results.append({
                'disease_name':    dtype,
                'season':          data['season'],
                'total_cases':     data['recent'] + data['older'],
                'trend_score':     score,
                'seasonal_weight': sw,
            })

        results.sort(key=lambda x: x['trend_score'], reverse=True)
        serializer = DiseaseTrendSerializer(results, many=True)
        return Response(serializer.data)


# ─── 1.2 Time-Series Aggregation → Time-Series API ───────────────────────────



class TimeSeriesView(APIView):
    """
    GET /api/disease-trends/timeseries/?days=7&disease=Flu

    1.2 Time-Series Aggregation — Group by date using TruncDate.
    Groups by disease. Supports last 7 / 30 days via ?days= param.
    Uses ORM aggregation — no Python loops.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end     = _get_date_range(request)
        disease_filter = request.query_params.get('disease', None)

        # TruncDate for date grouping — pure ORM
        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name')
            .annotate(case_count=Count('id'))
            .order_by('appt_date', 'disease__name')
        )

        if disease_filter:
            qs = qs.filter(disease__name__icontains=disease_filter)

        # Group by disease TYPE (strip numbers) per date
        # Use dict to merge "Flu 1", "Flu 2" etc into single "Flu" per date
        counts = defaultdict(int)
        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            key   = (row['appt_date'], dtype)
            counts[key] += row['case_count']

        if not counts:
            return Response([])

        results = [
            {
                'date':         d.isoformat() if hasattr(d, 'isoformat') else str(d),
                'disease_name': name,
                'case_count':   count,
            }
            for (d, name), count in sorted(counts.items())
        ]

        serializer = TimeSeriesPointSerializer(results, many=True)
        return Response(serializer.data)


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

        _, end      = _get_db_date_range(days)
        p2_end      = end
        p2_start    = end - timedelta(days=days)
        p1_end      = p2_start - timedelta(days=1)
        p1_start    = p1_end - timedelta(days=days)

        results = compare_disease_trends(p1_start, p1_end, p2_start, p2_end)

        if not results:
            return Response([])

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

        # Pure ORM — count per disease per season
        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
                disease__is_active=True,
            )
            .select_related('disease')
            .values('disease__name', 'disease__season')
            .annotate(case_count=Count('id'))
            .order_by('disease__season', '-case_count')
        )

        # Group by season, aggregate by disease type
        season_map = defaultdict(lambda: defaultdict(int))

        for row in qs:
            dtype  = get_disease_type(row['disease__name'])
            season = row['disease__season'] or 'Unknown'
            season_map[season][dtype] += row['case_count']

        # Build response per season
        seasons_out = {}
        for season, type_counts in season_map.items():
            total = sum(type_counts.values())
            sorted_diseases = sorted(type_counts.items(), key=lambda x: -x[1])
            seasons_out[season] = {
                'top_disease':       sorted_diseases[0][0] if sorted_diseases else None,
                'top_disease_count': sorted_diseases[0][1] if sorted_diseases else 0,
                'total_cases':       total,
                'diseases': [
                    {
                        'disease_name': d,
                        'case_count':   c,
                        'percentage':   round(c / total * 100, 1) if total > 0 else 0,
                    }
                    for d, c in sorted_diseases
                ],
            }

        # Overall total = sum of all appointments in range (not sum of seasons)
        overall_total = Appointment.objects.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        ).count()

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
            min_cases = int(request.query_params.get('min_cases', 10))
        except ValueError:
            min_cases = 10

        # Pure ORM aggregation — group by doctor + disease
        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('doctor', 'disease')
            .values(
                'doctor__id',
                'doctor__first_name',
                'doctor__last_name',
                'disease__name',
                'disease__season',
            )
            .annotate(case_count=Count('id'))
            .filter(case_count__gte=min_cases)   # ORM-level filter, not Python
            .order_by('-case_count')
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
            'total_rows': len(results),
            'data':       results,
        })


# ─── Weekly Report ────────────────────────────────────────────────────────────



