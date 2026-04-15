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
from ..services.restock_calculator import calculate_restock, apply_multi_disease_contribution
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

# restock_views.py extracted classes

class RestockSuggestionView(APIView):
    """
    GET /api/restock-suggestions/?days=30

    2.4 Demand Prediction:
        expected_demand = trend_count × avg_usage × safety_buffer
        avg_usage       = total_quantity / total_cases  (DB-driven, not hardcoded)

    2.5 Restock Calculation:
        restock = max(0, expected_demand - current_stock)

    Uses select_related. No Python loops for DB aggregation.
    Handles: zero stock, zero demand, new disease edge cases.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end    = _get_date_range(request)
        current_month = date.today().month
        mid           = end - timedelta(days=7)

        # ── 1.1 Disease case counts — ORM Count ──────────────────────
        appt_qs_base = Appointment.objects.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        appt_qs = apply_clinic_filter(appt_qs_base, request) \
            .select_related('disease') \
            .annotate(appt_date=TruncDate('appointment_datetime')) \
            .values('appt_date', 'disease__name', 'disease__season') \
            .annotate(day_count=Count('id'))

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season   = {}

        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']

        # ── 1.3 Medicine usage: avg_usage = Sum(qty)/Count(cases) ────
        disease_case_map = defaultdict(int)
        for dtype, day_map in daily_by_dtype.items():
            disease_case_map[dtype] = sum(day_map.values())

        # Sum(quantity) per drug — ORM Sum, no loops
        qty_qs_base = PrescriptionLine.objects.filter(
            prescription_date__range=(start, end),
            disease__isnull=False,
        )
        # Note: PrescriptionLine has a ForeignKey to Prescription, which has clinic.
        # But we can also use 'prescription__clinic' if clinic is on prescription.
        qty_qs = apply_clinic_filter(qty_qs_base, request, clinic_field='prescription__clinic') \
            .select_related('drug', 'disease') \
            .values('drug__drug_name', 'disease__name') \
            .annotate(total_qty=Sum('quantity'))

        drug_qty_map   = defaultdict(int)
        drug_cases_map = defaultdict(int)

        for row in qty_qs:
            drug_name = row['drug__drug_name']
            dtype     = get_disease_type(row['disease__name'])
            drug_qty_map[drug_name]   += row['total_qty'] or 0
            drug_cases_map[drug_name] += disease_case_map.get(dtype, 1)

        # DB-driven avg_usage per drug
        avg_usage_map = {
            drug: round(drug_qty_map[drug] / max(drug_cases_map[drug], 1), 4)
            for drug in drug_qty_map
        }

        # Disease contributions per drug — data-driven, no hardcoded mapping
        drug_disease_map = defaultdict(set)
        for row in qty_qs:
            dtype = get_disease_type(row['disease__name'])
            drug_disease_map[row['drug__drug_name']].add(dtype)

        # ── 2.1 + 2.2 Prediction logic per disease type ──────────────
        dtype_demand = {}
        for dtype in dtype_season:
            daily    = _build_daily_list(daily_by_dtype, dtype, start, end)
            forecast = moving_average_forecast(daily)
            trend    = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw     = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        # ── Stock map — Sum per drug name ─────────────────────────────
        stock_map = {
            r['drug_name']: r['total_stock']
            for r in DrugMaster.objects
            .values('drug_name')
            .annotate(total_stock=Sum('current_stock'))
        }

        # ── 2.5 Restock calculation for all drug names ────────────────
        all_drug_names = set(stock_map.keys()) | set(drug_qty_map.keys())
        results = []

        for drug_name in all_drug_names:
            current_stock = stock_map.get(drug_name, 0) or 0
            avg_usage     = avg_usage_map.get(drug_name, 1.0) or 1.0
            contributing  = list(drug_disease_map.get(drug_name, set()))

            if not contributing:
                contributing = list(dtype_demand.keys())

            disease_demands = [
                {
                    'predicted_demand': dtype_demand[d]['demand'],
                    'seasonal_weight':  dtype_demand[d]['seasonal_weight'],
                }
                for d in contributing if d in dtype_demand
            ]

            combined = (
                apply_multi_disease_contribution(disease_demands)
                if disease_demands else 0.0
            )

            suggestion = calculate_restock(
                drug_name=drug_name,
                generic_name=_get_generic(drug_name),
                predicted_demand=combined,
                avg_usage=avg_usage,
                current_stock=current_stock,
                contributing_diseases=contributing[:8]
            )
            results.append(suggestion)

        STATUS_ORDER = {'critical': 0, 'low': 1, 'sufficient': 2}
        results.sort(key=lambda x: (
            STATUS_ORDER.get(x['status'], 3),
            -x['suggested_restock']
        ))

        serializer = RestockSuggestionSerializer(results, many=True)
        return Response(serializer.data)


# ─── District Restock ─────────────────────────────────────────────────────────



class DistrictRestockView(APIView):
    """
    GET /api/district-restock/?district=Chennai&days=30

    District-level restock view.
    Returns district list when no district param given.
    Returns drug+strength+dosage detail for selected district.
    Demand prorated by clinic proportion per district.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        start, end      = _get_date_range(request)
        current_month   = date.today().month
        district_filter = request.query_params.get('district', None)
        district_search = None
        clinic_ids = []

        if not district_filter:
            # Multi-tenant logic: Clinic users only see THEIR clinic
            user = request.user
            profile = getattr(user, 'profile', None)
            
            if profile and profile.role == 'CLINIC_USER' and profile.clinic:
                all_clinics = [profile.clinic.clinic_name]
            else:
                all_clinics = Clinic.objects.values_list('clinic_name', flat=True).distinct()

            return Response({
                'districts': sorted(all_clinics),
                'total':     len(all_clinics),
            })

        # Shared demand computation - optimize with select_related
        appt_filter = {
            'appointment_datetime__date__range': (start, end),
            'disease__isnull': False,
        }
        if district_filter and clinic_ids:
            appt_filter['clinic__in'] = clinic_ids

        appt_qs = (
            Appointment.objects
            .filter(**appt_filter)
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name', 'disease__season')
            .annotate(day_count=Count('id'))
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season   = {}

        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']

        # Optimize queries by narrowing to clinics in the selected district.
        qty_filter = {
            'prescription_date__range': (start, end),
            'disease__isnull': False,
        }
        district_search = None
        clinic_ids = []
        if district_filter:
            clinic_ids = list(
                Clinic.objects
                .filter(clinic_name__icontains=district_filter.strip())
                .values_list('id', flat=True)
            )
            if not clinic_ids:
                return Response({
                    'district': district_filter,
                    'clinic_count': 0,
                    'period': f'{start} to {end}',
                    'results': [],
                    'summary': {'total_drugs': 0, 'critical': 0, 'low': 0, 'sufficient': 0}
                })
            qty_filter['prescription__clinic__in'] = clinic_ids
            selected_drug_names = list(
                DrugMaster.objects
                .filter(clinic__in=clinic_ids)
                .values_list('drug_name', flat=True)
                .distinct()
            )
        else:
            selected_drug_names = []

        qty_qs = (
            PrescriptionLine.objects
            .filter(**qty_filter)
            .select_related('drug', 'disease')
            .values('drug__drug_name', 'disease__name')
            .annotate(total_qty=Sum('quantity'))
        )

        disease_case_map = defaultdict(int)
        for dtype, day_map in daily_by_dtype.items():
            disease_case_map[dtype] = sum(day_map.values())

        drug_qty_map   = defaultdict(int)
        drug_cases_map = defaultdict(int)
        drug_disease_map = defaultdict(set)

        for row in qty_qs:
            drug_name = row['drug__drug_name']
            dtype     = get_disease_type(row['disease__name'])
            drug_qty_map[drug_name]   += row['total_qty'] or 0
            drug_cases_map[drug_name] += disease_case_map.get(dtype, 1)
            drug_disease_map[drug_name].add(dtype)

        avg_usage_map = {
            drug: round(drug_qty_map[drug] / max(drug_cases_map[drug], 1), 4)
            for drug in drug_qty_map
        }

        dtype_demand = {}
        for dtype in dtype_season:
            daily    = _build_daily_list(daily_by_dtype, dtype, start, end)
            forecast = moving_average_forecast(daily)
            trend    = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw     = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        def get_drug_demand(drug_name):
            contributing = list(drug_disease_map.get(drug_name, set()))
            if not contributing:
                contributing = list(dtype_demand.keys())
            demands = [
                {'predicted_demand': dtype_demand[d]['demand'],
                 'seasonal_weight':  dtype_demand[d]['seasonal_weight']}
                for d in contributing if d in dtype_demand
            ]
            avg_usage = avg_usage_map.get(drug_name, 1.0) or 1.0
            combined  = apply_multi_disease_contribution(demands) if demands else 0.0
            return round(combined * avg_usage * 1.2, 2), contributing

        if district_filter:
            drug_qs = (
                DrugMaster.objects
                .filter(
                    drug_name__in=selected_drug_names,
                    clinic__id__in=clinic_ids,
                )
                .select_related('clinic')
                .values(
                    'drug_name', 'generic_name',
                    'drug_strength', 'dosage_type',
                    'clinic__id', 'clinic__clinic_name',
                    'clinic__clinic_address_1', 'current_stock'
                )
            )
        else:
            drug_qs = (
                DrugMaster.objects
                .filter(drug_name__in=list(drug_qty_map.keys()))
                .select_related('clinic')
                .values(
                    'drug_name', 'generic_name',
                    'drug_strength', 'dosage_type',
                    'clinic__id', 'clinic__clinic_name',
                    'clinic__clinic_address_1', 'current_stock'
                )
            )

        district_drug = defaultdict(lambda: defaultdict(lambda: {
            'generic_name': '', 'total_stock': 0, 'clinic_count': 0
        }))

        for row in drug_qs:
            # Now "district" is actually the CLINIC NAME
            district = row['clinic__clinic_name']

            if district_filter and district.lower() != district_filter.lower():
                continue

            key = (
                row['drug_name'], row['generic_name'] or '',
                row['drug_strength'] or '', row['dosage_type'] or ''
            )
            entry = district_drug[district][key]
            entry['generic_name']  = row['generic_name'] or ''
            entry['total_stock']  += row['current_stock'] or 0
            entry['clinic_count'] += 1

        if not district_filter:
            # If all districts are "Unknown", fallback to clinic names
            if all_districts == {'Unknown'} or len(all_districts) == 0:
                clinics = Clinic.objects.values_list('clinic_name', flat=True).distinct()
                all_districts = set(clinics)
            
            return Response({
                'districts': sorted(all_districts),
                'total':     len(all_districts),
            })

        total_clinics = Clinic.objects.count() or 1
        STATUS_ORDER  = {'critical': 0, 'low': 1, 'sufficient': 2}
        results       = []
        max_clinics   = 0

        matched_key = next(
            (k for k in district_drug if k.lower() == district_filter.lower()),
            None
        )

        if not matched_key:
            return Response({
                'district': district_filter, 'clinic_count': 0,
                'period': f'{start} to {end}', 'results': [],
                'summary': {'total_drugs': 0, 'critical': 0, 'low': 0, 'sufficient': 0}
            })


        for (drug_name, generic, strength, dosage), data in district_drug[matched_key].items():
            max_clinics   = max(max_clinics, data['clinic_count'])
            system_demand, contributing = get_drug_demand(drug_name)
            district_ratio  = data['clinic_count'] / total_clinics
            district_demand = round(system_demand * district_ratio, 2)
            total_stock     = data['total_stock']
            suggested       = max(0, int(district_demand - total_stock))

            if total_stock == 0:
                status    = 'critical'
                suggested = max(1, int(district_demand))
            elif suggested == 0:
                status = 'sufficient'
            else:
                pct    = (district_demand - total_stock) / district_demand * 100 if district_demand > 0 else 100
                status = 'critical' if pct > 50 else 'low'

            results.append({
                'drug_name':             drug_name,
                'generic_name':          generic,
                'drug_strength':         strength,
                'dosage_type':           dosage,
                'district':              district_filter,
                'clinic_count':          data['clinic_count'],
                'current_stock':         total_stock,
                'predicted_demand':      district_demand,
                'suggested_restock':     suggested,
                'status':                status,
                'contributing_diseases': contributing[:6],
            })

        results.sort(key=lambda x: (STATUS_ORDER.get(x['status'], 3), x['drug_name']))

        return Response({
            'district':    district_filter,
            'clinic_count': max_clinics,
            'period':       f'{start} to {end}',
            'results':      results,
            'summary': {
                'total_drugs': len(results),
                'critical':    sum(1 for r in results if r['status'] == 'critical'),
                'low':         sum(1 for r in results if r['status'] == 'low'),
                'sufficient':  sum(1 for r in results if r['status'] == 'sufficient'),
            }
        })


# ─── Export Views ─────────────────────────────────────────────────────────────



class AdaptiveBufferView(APIView):
    """
    GET /api/adaptive-buffer/?days=30

    Calculates the adaptive safety buffer based on current spike activity.
    """
    def get(self, request):
        days = validate_positive_int(request.query_params.get('days'), 'days', default=30, min_value=1, max_value=365)
        start, end = _get_db_date_range(days)

        service = RestockService()
        result = service.calculate_adaptive_buffer(start_date=start, end_date=end)
        return Response(result)


