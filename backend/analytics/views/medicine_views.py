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
from ..services.spike_detector import detect_spike, get_seasonal_weight
from ..services.restock_calculator import calculate_restock, apply_multi_disease_contribution, calculate_dynamic_safety_buffer
from ..serializers.serializers import (
    DiseaseTrendSerializer, TimeSeriesPointSerializer,
    SpikeAlertSerializer, RestockSuggestionSerializer
)
from ..services.medicine_analytics import MedicineAnalyticsService
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

# medicine_views.py extracted classes

class MedicineUsageView(APIView):
    """
    GET /api/medicine-usage/?days=30

    1.3 Medicine Usage Aggregation.
    Task: Calculate total medicine usage per disease.
    Uses Sum(quantity) grouped by disease + medicine.
    avg_usage = total_quantity / total_cases  (DB-driven, no hardcoding)
    No Python loops for aggregation.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end = _get_date_range(request)

        # Step 1: Count total cases per disease type — ORM Count
        appt_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(total_cases=Count('id'))
        )

        disease_case_map = defaultdict(int)
        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            disease_case_map[dtype] += row['total_cases']

        if not disease_case_map:
            return Response([])

        # Step 2: Sum(quantity) grouped by drug + disease — ORM Sum
        usage_qs = (
            PrescriptionLine.objects
            .filter(
                prescription_date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('drug', 'disease')
            .values(
                'drug__drug_name',
                'drug__generic_name',
                'disease__name',
                'disease__season',
            )
            .annotate(
                total_quantity=Sum('quantity'),
                prescription_count=Count('id'),
            )
            .order_by('drug__drug_name', 'disease__name')
        )

        # Step 3: Aggregate by disease type, compute avg_usage per DB formula
        type_usage = defaultdict(lambda: defaultdict(lambda: {
            'generic_name': '', 'season': '', 'total_qty': 0, 'rx_count': 0
        }))

        for row in usage_qs:
            drug_name = row['drug__drug_name']
            dtype     = get_disease_type(row['disease__name'])
            entry     = type_usage[drug_name][dtype]
            entry['generic_name'] = row['drug__generic_name'] or ''
            entry['season']       = row['disease__season']
            entry['total_qty']   += row['total_quantity'] or 0
            entry['rx_count']    += row['prescription_count'] or 0

        if not type_usage:
            return Response([])

        results = []
        for drug_name, disease_map in type_usage.items():
            for dtype, data in disease_map.items():
                total_cases = disease_case_map.get(dtype, 1) or 1
                total_qty   = data['total_qty']

                # DB-driven formula: avg_usage = total_quantity / total_cases
                avg_usage = round(total_qty / total_cases, 4)

                results.append({
                    'drug_name':          drug_name,
                    'generic_name':       data['generic_name'],
                    'disease_name':       dtype,
                    'season':             data['season'],
                    'total_quantity':     total_qty,
                    'total_cases':        total_cases,
                    'avg_usage':          avg_usage,
                    'prescription_count': data['rx_count'],
                    'period_start':       str(start),
                    'period_end':         str(end),
                })

        results.sort(key=lambda x: (-x['total_quantity'], x['drug_name']))
        return Response(results)


# ─── 2.3 Spike Detection → Spike Alert API ───────────────────────────────────



class TopMedicinesView(APIView):
    """
    GET /api/top-medicines/?days=30&limit=10

    Shows current stock per drug from DrugMaster (not prescription-based).
    Prescription count = total prescriptions written in period (for context).
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end = _get_date_range(request)
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10
        limit = min(max(limit, 1), 50)

        # Find top medicines by usage in one aggregated query.
        usage_qs = (
            PrescriptionLine.objects
            .filter(prescription_date__range=(start, end))
            .values(
                'drug__id', 'drug__drug_name', 'drug__generic_name', 'drug__dosage_type'
            )
            .annotate(
                current_stock=Sum('drug__current_stock'),
                variant_count=Count('drug', distinct=True),
                prescription_count=Count('id'),
                total_quantity=Sum('quantity'),
            )
            .order_by('-total_quantity', '-prescription_count')
        )

        total_drugs = usage_qs.count()
        top_rows = list(usage_qs[:limit])

        results = []
        for row in top_rows:
            results.append({
                'drug_name':          row['drug__drug_name'],
                'generic_name':       row['drug__generic_name'] or '',
                'dosage_type':        row['drug__dosage_type'] or '',
                'current_stock':      row['current_stock'] or 0,
                'prescription_count': row['prescription_count'] or 0,
                'total_quantity':     row['total_quantity'] or 0,
                'variant_count':      row['variant_count'] or 0,
                'note':              'Top medicines are sorted by usage, not stock',
            })

        return Response({
            'period':        f'{start} to {end}',
            'total_drugs':   total_drugs,
            'top_medicines': results,
        })

# ── New Feature 3: Low Stock Alert System ────────────────────────────────────



class LowStockAlertView(APIView):
    """
    GET /api/low-stock-alerts/?threshold=50

    Uses average stock per clinic per drug, not system total.
    This makes the threshold meaningful at clinic level.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        try:
            threshold = int(request.query_params.get('threshold', 50))
        except ValueError:
            threshold = 50

        from django.db.models import Avg as DAvg, Count as DCount

        # Average stock per clinic per drug — meaningful comparison
        stock_qs = (
            DrugMaster.objects
            .values('drug_name', 'generic_name')
            .annotate(
                avg_stock=DAvg('current_stock'),
                total_stock=Sum('current_stock'),
                clinic_count=DCount('clinic', distinct=True),
            )
            .filter(avg_stock__isnull=False)  # Avoid null values
            .order_by('avg_stock')
        )

        results = []
        out_of_stock = critical = low = warning = 0

        for row in stock_qs:
            avg = round(row['avg_stock'] or 0, 1)
            total = row['total_stock'] or 0

            # Alert based on AVERAGE per clinic vs threshold
            if avg > threshold:
                continue    # not an alert

            if avg == 0:
                alert_level = 'out_of_stock'
                out_of_stock += 1
            elif avg <= threshold * 0.25:
                alert_level = 'critical'
                critical += 1
            elif avg <= threshold * 0.5:
                alert_level = 'low'
                low += 1
            else:
                alert_level = 'warning'
                warning += 1

            results.append({
                'drug_name':    row['drug_name'],
                'generic_name': row['generic_name'] or '',
                'avg_stock_per_clinic': avg,
                'total_stock':  total,
                'clinic_count': row['clinic_count'],
                'threshold':    threshold,
                'alert_level':  alert_level,
                'restock_now':  avg == 0 or alert_level == 'critical',
            })

        return Response({
            'threshold':     threshold,
            'note':          'Based on average stock per clinic',
            'total_alerts':  len(results),
            'out_of_stock':  out_of_stock,
            'critical':      critical,
            'low':           low,
            'warning':       warning,
            'alerts':        results,
        })

# ─── Seasonality ───────────────────────────



class MedicineDependencyView(APIView):
    """
    GET /api/medicine-dependency/?days=30&disease=Flu

    Returns which medicines are most commonly used for each disease.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        days = validate_positive_int(request.query_params.get('days'), 'days', default=30, min_value=1, max_value=365)
        min_usage = validate_positive_int(request.query_params.get('min_usage'), 'min_usage', default=0, min_value=0)
        disease_name = request.query_params.get('disease')
        start, end = _get_db_date_range(days)

        service = MedicineAnalyticsService()
        result = service.map_medicine_dependencies(
            disease_name=disease_name,
            start_date=start,
            end_date=end,
            min_usage=min_usage,
        )
        return Response(result)




class StockDepletionForecastView(APIView):
    """
    GET /api/stock-depletion/?drug_id=5&days=30

    Provides stock depletion forecast for a specific medicine.
    """
    def get(self, request):
        drug_id = request.query_params.get('drug_id')
        drug_name = request.query_params.get('drug_name')
        if not drug_id and not drug_name:
            return Response(
                {'error': 'Provide drug_id or drug_name'},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        days = validate_positive_int(request.query_params.get('days'), 'days', default=30, min_value=1, max_value=365)
        start, end = _get_db_date_range(days)

        if not drug_id:
            match = DrugMaster.objects.filter(drug_name__icontains=drug_name).first()
            if not match:
                return Response({'error': 'Drug not found'}, status=drf_status.HTTP_404_NOT_FOUND)
            drug_id = match.id

        service = MedicineAnalyticsService()
        result = service.forecast_stock_depletion(
            drug_id=int(drug_id),
            start_date=start,
            end_date=end,
            forecast_days=validate_positive_int(request.query_params.get('forecast_days'), 'forecast_days', default=30, min_value=1, max_value=90)
        )

        if result.get('error'):
            return Response(result, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(result)




