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

# spike_views.py extracted classes

class SpikeAlertView(APIView):
    """
    GET /api/spike-alerts/?days=8&all=true
    GET /api/spike-detection/?days=8&all=true  (alias)

    2.3 Spike Detection: today_count > (mean_last_N_days + 2 × std_dev)
    Configurable baseline window via ?days= param (minimum 8).
    Returns period_count = total cases across the selected window.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        show_all = request.query_params.get('all', 'false').lower() == 'true'
        
        # Hardcoded to 8 days baseline window (7 days + today) as per fixed formula
        days = 8
        latest = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        end   = latest.date() if latest else date.today()
        start = end - timedelta(days=days)

        # ORM aggregation — group by date and disease type
        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name', 'disease__season')
            .annotate(day_count=Count('id'))
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        type_season    = {}

        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            type_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']

        if not type_season:
            return Response([])

        baseline_days = days - 1
        results = []

        for dtype in type_season:
            daily_counts = _build_daily_list(daily_by_dtype, dtype, start, end)
            spike_info   = detect_spike(daily_counts, baseline_days=baseline_days)
            period_count = sum(daily_counts)

            if spike_info['is_spike'] or show_all:
                results.append({
                    'disease_name': dtype,
                    'period_count': period_count,
                    **spike_info
                })

        results.sort(key=lambda x: x['today_count'], reverse=True)
        serializer = SpikeAlertSerializer(results, many=True)
        return Response(serializer.data)


# ─── 2.4 + 2.5 Demand & Restock → Restock Suggestions API ───────────────────



