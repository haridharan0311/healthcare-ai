import csv
import re
from datetime import date, timedelta
from collections import defaultdict

from django.http import HttpResponse
from django.db.models import Count, Avg, Max, Sum, Min
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from .models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic

from .ml_engine import (
    moving_average_forecast, weighted_trend_score, predict_demand
)
from .spike_detector import detect_spike, get_seasonal_weight
from .restock_calculator import calculate_restock, apply_multi_disease_contribution
from .serializers import (
    DiseaseTrendSerializer, TimeSeriesPointSerializer,
    SpikeAlertSerializer, RestockSuggestionSerializer
)

# ─── Generic name lookup (no hardcoded disease mapping) ──────────────────────
GENERIC_MAP = {
    'Paracetamol':       'Acetaminophen',
    'Ibuprofen':         'Ibuprofen',
    'Amoxicillin':       'Amoxicillin trihydrate',
    'Metformin':         'Metformin hydrochloride',
    'Aspirin':           'Acetylsalicylic acid',
    'Cetirizine':        'Cetirizine hydrochloride',
    'Azithromycin':      'Azithromycin dihydrate',
    'Ciprofloxacin':     'Ciprofloxacin hydrochloride',
    'Doxycycline':       'Doxycycline hyclate',
    'Diclofenac':        'Diclofenac sodium',
    'Chlorpheniramine':  'Chlorpheniramine maleate',
    'Montelukast':       'Montelukast sodium',
    'Glibenclamide':     'Glibenclamide',
    'Glimepiride':       'Glimepiride',
    'Insulin (Regular)': 'Human insulin',
    'Amlodipine':        'Amlodipine besylate',
    'Atenolol':          'Atenolol',
    'Losartan':          'Losartan potassium',
    'Enalapril':         'Enalapril maleate',
    'Salbutamol':        'Albuterol sulfate',
    'Prednisolone':      'Prednisolone',
    'Theophylline':      'Theophylline anhydrous',
    'Omeprazole':        'Omeprazole magnesium',
    'Ranitidine':        'Ranitidine hydrochloride',
    'Domperidone':       'Domperidone',
    'Vitamin C':         'Ascorbic acid',
    'Vitamin D3':        'Cholecalciferol',
    'Zinc Sulphate':     'Zinc sulfate monohydrate',
    'ORS':               'Oral Rehydration Salts',
    'Chloroquine':       'Chloroquine phosphate',
}


def _get_generic(drug_name: str) -> str:
    return GENERIC_MAP.get(drug_name, drug_name)


def get_disease_type(name: str) -> str:
    """Strip trailing numbers from synthetic disease names. No hardcoding."""
    return re.sub(r'\s+\d+$', '', name).strip()


def _extract_district(address: str) -> str:
    """
    Extract district from TN address format.
    No.X, street, area, town, District, Tamil Nadu - PIN. Ph: X
    District is always the 5th comma-separated segment.
    """
    if not address:
        return 'Unknown'
    parts = [p.strip() for p in address.split(',')]
    return parts[4].strip() if len(parts) >= 5 else 'Unknown'


# ─── Shared date helpers ─────────────────────────────────────────────────────

def _get_db_date_range(days: int = 30):
    """
    All date windows relative to latest DB date — no caching.
    Ensures APIs always return latest data.
    """
    latest = Appointment.objects.aggregate(
        latest=Max('appointment_datetime')
    )['latest']
    end   = latest.date() if latest else date.today()
    start = end - timedelta(days=days)
    return start, end


def _get_date_range(request):
    try:
        days = int(request.query_params.get('days', 30))
    except ValueError:
        days = 30
    return _get_db_date_range(days)


def _build_daily_list(daily_by_dtype: dict, dtype: str,
                      start: date, end: date) -> list:
    """Build ordered daily count list for a disease type."""
    counts = []
    cursor = start
    while cursor <= end:
        counts.append(daily_by_dtype[dtype].get(cursor, 0))
        cursor += timedelta(days=1)
    return counts


# ─── 1.1 Disease Aggregation → Disease Trends API ────────────────────────────

class DiseaseTrendView(APIView):
    """
    GET /api/disease-trends/?days=30

    1.1 Disease Aggregation — Count cases per disease using ORM Count.
    No Python loops for aggregation. Uses select_related for performance.
    Supports date filtering via ?days= param.
    """
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
            .order_by('appt_date')
        )

        if disease_filter:
            qs = qs.filter(disease__name__icontains=disease_filter)

        # Group by disease type — aggregate across numbered variants
        counts = defaultdict(int)
        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            if disease_filter and dtype.lower() != disease_filter.lower():
                continue
            key = (row['appt_date'], dtype)
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

class MedicineUsageView(APIView):
    """
    GET /api/medicine-usage/?days=30

    1.3 Medicine Usage Aggregation.
    Task: Calculate total medicine usage per disease.
    Uses Sum(quantity) grouped by disease + medicine.
    avg_usage = total_quantity / total_cases  (DB-driven, no hardcoding)
    No Python loops for aggregation.
    """
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
                prescription__prescription_date__range=(start, end),
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

class SpikeAlertView(APIView):
    """
    GET /api/spike-alerts/?days=8&all=true
    GET /api/spike-detection/?days=8&all=true  (alias)

    2.3 Spike Detection: today_count > (mean_last_N_days + 2 × std_dev)
    Configurable baseline window via ?days= param (minimum 8).
    Returns period_count = total cases across the selected window.
    """
    def get(self, request):
        show_all = request.query_params.get('all', 'false').lower() == 'true'

        try:
            days = int(request.query_params.get('days', 8))
        except ValueError:
            days = 8
        days = max(days, 8)

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
    def get(self, request):
        start, end    = _get_date_range(request)
        current_month = date.today().month
        mid           = end - timedelta(days=7)

        # ── 1.1 Disease case counts — ORM Count ──────────────────────
        appt_qs = (
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
        dtype_season   = {}

        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']

        # ── 1.3 Medicine usage: avg_usage = Sum(qty)/Count(cases) ────
        # Total cases per disease type
        disease_case_map = defaultdict(int)
        for dtype, day_map in daily_by_dtype.items():
            disease_case_map[dtype] = sum(day_map.values())

        # Sum(quantity) per drug — ORM Sum, no loops
        qty_qs = (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('drug', 'disease')
            .values('drug__drug_name', 'disease__name')
            .annotate(total_qty=Sum('quantity'))
        )

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
    def get(self, request):
        start, end      = _get_date_range(request)
        current_month   = date.today().month
        district_filter = request.query_params.get('district', None)

        # Shared demand computation
        appt_qs = (
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
        dtype_season   = {}

        for row in appt_qs:
            dtype = get_disease_type(row['disease__name'])
            dtype_season[dtype] = row['disease__season']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']

        qty_qs = (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False,
            )
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

        # Load DrugMaster with clinic addresses
        drug_qs = (
            DrugMaster.objects
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
        all_districts = set()

        for row in drug_qs:
            district = _extract_district(row['clinic__clinic_address_1'])
            all_districts.add(district)
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
            return Response({
                'districts': sorted(all_districts),
                'total':     len(all_districts),
            })

        total_clinics = Clinic.objects.count() or 1
        STATUS_ORDER  = {'critical': 0, 'low': 1, 'sufficient': 2}
        results       = []
        max_clinics   = 0

        for (drug_name, generic, strength, dosage), data in district_drug[district_filter].items():
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

class ExportDiseaseTrendsView(APIView):
    """GET /api/export/disease-trends/ — CSV download"""
    def get(self, request):
        start, end    = _get_date_range(request)
        current_month = date.today().month
        mid           = end - timedelta(days=7)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="disease_trends_{end}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'Disease', 'Season', 'Category', 'Severity',
            'Total Cases', 'Recent Cases (7d)', 'Older Cases',
            'Trend Score', 'Seasonal Weight', 'Status',
            'Period Start', 'Period End'
        ])

        recent_qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(mid, end), disease__isnull=False)
            .select_related('disease')
            .values('disease__name', 'disease__season',
                    'disease__category', 'disease__severity')
            .annotate(cnt=Count('id'))
        )
        older_qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, mid), disease__isnull=False)
            .select_related('disease')
            .values('disease__name')
            .annotate(cnt=Count('id'))
        )

        older_map = {get_disease_type(r['disease__name']): r['cnt'] for r in older_qs}
        type_data = defaultdict(lambda: {'season': 'All', 'category': '', 'severity': 1, 'recent': 0, 'older': 0})

        for row in recent_qs:
            dtype = get_disease_type(row['disease__name'])
            type_data[dtype].update({
                'season': row['disease__season'],
                'category': row['disease__category'] or '',
                'severity': row['disease__severity'],
            })
            type_data[dtype]['recent'] += row['cnt']
            type_data[dtype]['older']  += older_map.get(dtype, 0)

        rows = []
        for dtype, data in type_data.items():
            sw     = get_seasonal_weight(data['season'], current_month)
            score  = round(weighted_trend_score(data['recent'], data['older']) * sw, 2)
            total  = data['recent'] + data['older']
            status = 'High' if score > 50 else 'Moderate' if score > 20 else 'Low'
            rows.append((dtype, data['season'], data['category'], data['severity'],
                         total, data['recent'], data['older'], score, sw, status, start, end))

        rows.sort(key=lambda x: x[7], reverse=True)
        for row in rows:
            writer.writerow(row)
        return response


class ExportSpikeAlertsView(APIView):
    """GET /api/export/spike-alerts/ — CSV download"""
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 8))
        except ValueError:
            days = 8
        days = max(days, 8)

        latest = Appointment.objects.aggregate(latest=Max('appointment_datetime'))['latest']
        end    = latest.date() if latest else date.today()
        start  = end - timedelta(days=days)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="spike_alerts_{end}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Disease', 'Season', 'Today Count', 'Period Count',
            'Mean (baseline)', 'Std Dev', 'Threshold',
            'Is Spike', 'Severity', 'Baseline Days', 'As Of Date'
        ])

        qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end), disease__isnull=False)
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name', 'disease__season', 'disease__severity')
            .annotate(day_count=Count('id'))
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        type_season    = {}
        type_severity  = {}

        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            type_season[dtype]   = row['disease__season']
            type_severity[dtype] = row['disease__severity']
            daily_by_dtype[dtype][row['appt_date']] += row['day_count']

        baseline_days = days - 1
        rows = []
        for dtype in type_season:
            daily  = _build_daily_list(daily_by_dtype, dtype, start, end)
            s      = detect_spike(daily, baseline_days=baseline_days)
            period = sum(daily)
            rows.append([
                dtype, type_season[dtype], s['today_count'], period,
                s['mean_last_7_days'], s['std_dev'], s['threshold'],
                'YES' if s['is_spike'] else 'no',
                type_severity.get(dtype, 1), baseline_days, end,
            ])

        rows.sort(key=lambda x: (0 if x[7] == 'YES' else 1, -x[2]))
        for row in rows:
            writer.writerow(row)
        return response


class ExportRestockView(APIView):
    """GET /api/export/restock/ — detailed CSV per DrugMaster row"""
    def get(self, request):
        start, end    = _get_date_range(request)
        current_month = date.today().month

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="restock_suggestions_{end}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'Drug Name', 'Generic Name', 'Drug Strength', 'Dosage Type',
            'Clinic Name', 'District',
            'Current Stock', 'Predicted Demand',
            'Suggested Restock', 'Status',
            'Contributing Diseases', 'Period'
        ])

        # Demand computation (ORM only)
        appt_qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end), disease__isnull=False)
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

        disease_case_map = {dtype: sum(dm.values()) for dtype, dm in daily_by_dtype.items()}

        qty_qs = (
            PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end), disease__isnull=False)
            .select_related('drug', 'disease')
            .values('drug__drug_name', 'disease__name')
            .annotate(total_qty=Sum('quantity'))
        )

        drug_qty_map     = defaultdict(int)
        drug_cases_map   = defaultdict(int)
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
            trend    = weighted_trend_score(sum(daily[-7:]), sum(daily[:-7]) if len(daily) > 7 else 0)
            demand   = predict_demand(trend, forecast)
            sw       = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        total_clinics = Clinic.objects.count() or 1

        grouped = (
            DrugMaster.objects
            .select_related('clinic')
            .values('drug_name', 'generic_name', 'drug_strength', 'dosage_type',
                    'clinic__clinic_name', 'clinic__clinic_address_1')
            .annotate(total_stock=Sum('current_stock'))
            .order_by('drug_name', 'clinic__clinic_name')
        )

        STATUS_ORDER = {'critical': 0, 'low': 1, 'sufficient': 2}
        rows = []

        for g in grouped:
            drug_name     = g['drug_name']
            current_stock = g['total_stock'] or 0
            avg_usage     = avg_usage_map.get(drug_name, 1.0) or 1.0
            contributing  = list(drug_disease_map.get(drug_name, set())) or list(dtype_demand.keys())

            demands = [
                {'predicted_demand': dtype_demand[d]['demand'],
                 'seasonal_weight':  dtype_demand[d]['seasonal_weight']}
                for d in contributing if d in dtype_demand
            ]
            combined        = apply_multi_disease_contribution(demands) if demands else 0.0
            clinic_count    = DrugMaster.objects.filter(
                drug_name=drug_name,
                clinic__clinic_name=g['clinic__clinic_name']
            ).count() or 1
            district_ratio  = clinic_count / total_clinics
            district_demand = round(combined * avg_usage * 1.2 * district_ratio, 2)
            suggested       = max(0, int(district_demand - current_stock))

            if current_stock == 0:
                status    = 'critical'
                suggested = max(1, int(district_demand))
            elif suggested == 0:
                status = 'sufficient'
            else:
                pct    = (district_demand - current_stock) / district_demand * 100 if district_demand > 0 else 100
                status = 'critical' if pct > 50 else 'low'

            district = _extract_district(g['clinic__clinic_address_1'])
            rows.append([
                drug_name, g['generic_name'] or '', g['drug_strength'] or '',
                g['dosage_type'] or '', g['clinic__clinic_name'] or '', district,
                current_stock, district_demand, suggested, status,
                ', '.join(contributing[:5]), f'{start} to {end}',
            ])

        rows.sort(key=lambda x: (STATUS_ORDER.get(x[9], 3), x[0], x[4]))
        for row in rows:
            writer.writerow(row)
        return response


class ExportReportView(APIView):
    """GET /api/export-report/ — combined CSV (legacy, kept for compatibility)"""
    def get(self, request):
        start, end    = _get_date_range(request)
        current_month = date.today().month
        mid           = end - timedelta(days=7)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="health_report_{end}.csv"'
        )
        writer = csv.writer(response)

        # Section 1
        writer.writerow([])
        writer.writerow(['DISEASE TREND REPORT', f'Period: {start} to {end}'])
        writer.writerow(['Disease', 'Season', 'Total Cases', 'Trend Score', 'Seasonal Weight', 'Status'])

        recent_qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(mid, end), disease__isnull=False)
            .select_related('disease')
            .values('disease__name', 'disease__season')
            .annotate(cnt=Count('id'))
        )
        older_qs = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, mid), disease__isnull=False)
            .select_related('disease')
            .values('disease__name')
            .annotate(cnt=Count('id'))
        )
        older_map = {get_disease_type(r['disease__name']): r['cnt'] for r in older_qs}
        type_data = defaultdict(lambda: {'season': 'All', 'recent': 0, 'older': 0})

        for row in recent_qs:
            dtype = get_disease_type(row['disease__name'])
            type_data[dtype]['season']  = row['disease__season']
            type_data[dtype]['recent'] += row['cnt']
            type_data[dtype]['older']  += older_map.get(dtype, 0)

        rows = []
        for dtype, data in type_data.items():
            sw     = get_seasonal_weight(data['season'], current_month)
            score  = round(weighted_trend_score(data['recent'], data['older']) * sw, 2)
            total  = data['recent'] + data['older']
            status = 'High' if score > 50 else 'Moderate' if score > 20 else 'Low'
            rows.append((dtype, data['season'], total, score, sw, status))
        for row in sorted(rows, key=lambda x: x[3], reverse=True):
            writer.writerow(row)

        # Section 2
        writer.writerow([])
        writer.writerow(['SPIKE ALERTS', f'As of: {end}'])
        writer.writerow(['Disease', 'Today Count', 'Mean (7d)', 'Std Dev', 'Threshold', 'Spike?'])
        for dtype, data in type_data.items():
            qs2 = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(end - timedelta(days=8), end),
                    disease__name__icontains=dtype
                )
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('appt_date')
                .annotate(cnt=Count('id'))
            )
            d_map = {row['appt_date']: row['cnt'] for row in qs2}
            daily = _build_daily_list(defaultdict(lambda: d_map, {dtype: d_map}),
                                      dtype, end - timedelta(days=8), end)
            s = detect_spike(daily)
            writer.writerow([dtype, s['today_count'], s['mean_last_7_days'],
                             s['std_dev'], s['threshold'], 'YES' if s['is_spike'] else 'no'])

        # Section 3
        writer.writerow([])
        writer.writerow(['RESTOCK SUGGESTIONS'])
        writer.writerow(['Drug', 'Generic Name', 'Current Stock', 'Predicted Demand', 'Suggested Restock', 'Status'])
        stock_map = {
            r['drug_name']: r['total']
            for r in DrugMaster.objects.values('drug_name').annotate(total=Sum('current_stock'))
        }
        for drug_name, stock in sorted(stock_map.items()):
            status = 'critical' if stock == 0 else 'sufficient'
            writer.writerow([drug_name, _get_generic(drug_name), stock, '—', '—', status])

        return response