import csv
from datetime import date, timedelta
from collections import defaultdict
from tracemalloc import start

from django.db.models.functions import Upper
from django.db.models import Value
import re

from django.http import HttpResponse
from django.db.models import Count, Avg, Max, Sum
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic

from .ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from .spike_detector import detect_spike, get_seasonal_weight
from .restock_calculator import calculate_restock, apply_multi_disease_contribution
from .serializers import (
    DiseaseTrendSerializer, TimeSeriesPointSerializer,
    SpikeAlertSerializer, RestockSuggestionSerializer
)


# ─── helpers ────────────────────────────────────────────────────────────────


def get_disease_type(name: str) -> str:
    """Strip trailing numbers from synthetic disease names.
    'Dengue 1842' → 'Dengue', 'COVID-19 553' → 'COVID-19'
    """
    return re.sub(r'\s+\d+$', '', name).strip()

def _daily_counts_for_disease(disease_name, start, end):
    """
    Return an ordered list of daily case counts for one disease
    between start and end date (inclusive). Fills missing days with 0.
    """
    qs = (
        Appointment.objects
        .filter(
            disease__name=disease_name,
            appointment_datetime__date__range=(start, end)
        )
        .values('appointment_datetime__date')
        .annotate(count=Count('id'))
        .order_by('appointment_datetime__date')
    )

    count_by_date = {row['appointment_datetime__date']: row['count'] for row in qs}

    counts = []
    cursor = start
    while cursor <= end:
        counts.append(count_by_date.get(cursor, 0))
        cursor += timedelta(days=1)
    return counts

def _get_db_date_range(days=30):
    """
    Instead of using today's calendar date (which has no data),
    find the latest appointment date in DB and work backwards from there.
    Falls back to calendar today if DB is empty.
    """
    latest = Appointment.objects.aggregate(
        latest=Max('appointment_datetime')
    )['latest']

    if latest:
        end = latest.date()
    else:
        end = date.today()

    start = end - timedelta(days=days)
    return start, end

def _get_date_range(request):
    """Read ?days=7 or ?days=30 from query params. Default 30."""
    try:
        days = int(request.query_params.get('days', 30))
    except ValueError:
        days = 30
    return _get_db_date_range(days)   # ← use DB-relative dates

# Add this near the top of views.py, after imports
GENERIC_MAP = {
    'Paracetamol': 'Acetaminophen',
    'Ibuprofen':   'Ibuprofen',
    'Amoxicillin': 'Amoxicillin trihydrate',
    'Metformin':   'Metformin hydrochloride',
    'Aspirin':     'Acetylsalicylic acid',
    'Cetirizine':  'Cetirizine hydrochloride',
}

def _get_generic(drug_name: str) -> str:
    return GENERIC_MAP.get(drug_name, drug_name)


# ─── District-level Restock View ─────────────────────────────────────────────

def _extract_district(address: str) -> str:
    """Extract district from TN address format:
    No.X, street, area, town, District, Tamil Nadu - PIN. Ph: X
    District is the 5th comma-separated part.
    """
    if not address:
        return 'Unknown'
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 5:
        return parts[4].strip()
    return 'Unknown'


class DistrictRestockView(APIView):
    """
    GET /api/district-restock/?days=30&district=Chennai
    Returns drug-level restock grouped by district.
    If no district given, returns list of all districts.
    Each row = one drug variant (name + strength + dosage) per district.
    """
    def get(self, request):
        start, end     = _get_date_range(request)
        current_month  = date.today().month
        district_filter = request.query_params.get('district', None)

        # ── 1. Build demand per disease type ─────────────────────────
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season   = {}

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            dtype_season[dtype] = appt.disease.season
            daily_by_dtype[dtype][appt.appointment_datetime.date()] += 1

        def build_daily_list(dtype):
            counts = []
            cursor = start
            while cursor <= end:
                counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)
            return counts

        dtype_demand = {}
        for dtype in dtype_season:
            daily    = build_daily_list(dtype)
            forecast = moving_average_forecast(daily)
            trend    = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw     = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        # ── 2. Disease contributions per drug ────────────────────────
        drug_disease_map = defaultdict(set)
        for line in (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False
            )
            .select_related('drug', 'disease')
        ):
            dtype = get_disease_type(line.disease.name)
            drug_disease_map[line.drug.drug_name].add(dtype)

        avg_qty_map = {
            r['drug__drug_name']: r['avg_qty']
            for r in PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end))
            .values('drug__drug_name')
            .annotate(avg_qty=Avg('quantity'))
        }

        # ── 3. Compute combined demand per drug name ─────────────────
        def get_drug_demand(drug_name):
            contributing = list(drug_disease_map.get(drug_name, set()))
            if not contributing:
                contributing = list(dtype_demand.keys())
            disease_demands = [
                {
                    'predicted_demand': dtype_demand[d]['demand'],
                    'seasonal_weight':  dtype_demand[d]['seasonal_weight'],
                }
                for d in contributing if d in dtype_demand
            ]
            combined = apply_multi_disease_contribution(disease_demands) if disease_demands else 0.0
            avg_qty  = avg_qty_map.get(drug_name, 1.5) or 1.5
            return round(combined * avg_qty * 1.2, 2), contributing

        # ── 4. Load all DrugMaster rows, extract district ─────────────
        drug_qs = (
            DrugMaster.objects
            .select_related('clinic')
            .values(
                'drug_name', 'generic_name',
                'drug_strength', 'dosage_type',
                'clinic__clinic_address_1',
                'current_stock'
            )
        )

        # ── 5. Group: district → drug_name+strength+dosage → stock ───
        # Structure: {district: {(drug,strength,dosage): {stock, generic, diseases}}}
        district_drug = defaultdict(lambda: defaultdict(lambda: {
            'generic_name': '',
            'total_stock': 0,
            'clinic_count': 0,
        }))

        all_districts = set()

        for row in drug_qs:
            district = _extract_district(row['clinic__clinic_address_1'])
            all_districts.add(district)

            if district_filter and district.lower() != district_filter.lower():
                continue

            key = (
                row['drug_name'],
                row['generic_name'] or '',
                row['drug_strength'] or '',
                row['dosage_type'] or '',
            )
            entry = district_drug[district][key]
            entry['generic_name']  = row['generic_name'] or ''
            entry['total_stock']  += row['current_stock'] or 0
            entry['clinic_count'] += 1

        # ── 6. Return district list if no filter ──────────────────────
        if not district_filter:
            return Response({
                'districts': sorted(all_districts),
                'total':     len(all_districts),
            })

        # ── 7. Build result rows for selected district ────────────────
        results = []
        total_clinics_in_district = 0

        for (drug_name, generic, strength, dosage), data in district_drug[district_filter].items():
            total_clinics_in_district = max(total_clinics_in_district, data['clinic_count'])
            system_demand, contributing = get_drug_demand(drug_name)

            # Prorate demand to this district based on clinic proportion
            all_clinics = Clinic.objects.count() or 1
            district_ratio  = data['clinic_count'] / all_clinics
            district_demand = round(system_demand * district_ratio, 2)

            total_stock = data['total_stock']
            suggested   = max(0, int(district_demand - total_stock))

            if total_stock == 0:
                status = 'critical'
                suggested = max(1, int(district_demand))
            elif suggested == 0:
                status = 'sufficient'
            else:
                pct = (district_demand - total_stock) / district_demand * 100 if district_demand > 0 else 100
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

        # Sort: critical → low → sufficient, then by drug name
        STATUS_ORDER = {'critical': 0, 'low': 1, 'sufficient': 2}
        results.sort(key=lambda x: (STATUS_ORDER.get(x['status'], 3), x['drug_name'], x['drug_strength']))

        return Response({
            'district':    district_filter,
            'clinic_count': total_clinics_in_district,
            'period':       f'{start} to {end}',
            'results':      results,
            'summary': {
                'total_drugs':  len(results),
                'critical':     sum(1 for r in results if r['status'] == 'critical'),
                'low':          sum(1 for r in results if r['status'] == 'low'),
                'sufficient':   sum(1 for r in results if r['status'] == 'sufficient'),
            }
        })


# ─── View 1: Disease Trends ──────────────────────────────────────────────────

class DiseaseTrendView(APIView):
    """
    GET /api/disease-trends/?days=30
    Returns all active diseases ranked by weighted trend score.
    Applies seasonal multiplier to boost in-season diseases.
    """
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        # Get all appointments in range, annotate with disease info
        appointments = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        # Group manually by disease TYPE (strip trailing number)
        from collections import defaultdict
        type_data = defaultdict(lambda: {
            'season': 'All', 'recent': 0, 'older': 0
        })

        for appt in appointments:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            type_data[dtype]['season'] = appt.disease.season
            appt_date = appt.appointment_datetime.date()
            if appt_date > mid:
                type_data[dtype]['recent'] += 1
            else:
                type_data[dtype]['older'] += 1

        results = []
        for disease_name, data in type_data.items():
            seasonal_weight = get_seasonal_weight(data['season'], current_month)
            trend_score = weighted_trend_score(data['recent'], data['older'])
            adjusted_score = round(trend_score * seasonal_weight, 2)
            results.append({
                'disease_name': disease_name,
                'season': data['season'],
                'total_cases': data['recent'] + data['older'],
                'trend_score': adjusted_score,
                'seasonal_weight': seasonal_weight,
            })

        results.sort(key=lambda x: x['trend_score'], reverse=True)
        serializer = DiseaseTrendSerializer(results, many=True)
        return Response(serializer.data)

# ─── View 2: Time-Series ─────────────────────────────────────────────────────

class TimeSeriesView(APIView):
    """
    GET /api/disease-trends/timeseries/?days=30&disease=Dengue
    Returns daily case counts per disease for graph plotting.
    Optional ?disease= filter for a single disease.
    """
    def get(self, request):
        start, end = _get_date_range(request)
        disease_filter = request.query_params.get('disease', None)

        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        from collections import defaultdict
        # {(date, disease_type): count}
        counts = defaultdict(int)
        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            if disease_filter and dtype.lower() != disease_filter.lower():
                continue
            counts[(appt.appointment_datetime.date(), dtype)] += 1

        results = [
            {'date': d, 'disease_name': name, 'case_count': count}
            for (d, name), count in sorted(counts.items())
        ]

        serializer = TimeSeriesPointSerializer(results, many=True)
        return Response(serializer.data)


# ─── View 3: Spike Alerts ────────────────────────────────────────────────────

class SpikeAlertView(APIView):
    """
    GET /api/spike-alerts/?all=true&days=7
    days param controls the baseline window.
    Minimum enforced at 8 (7-day baseline + today).
    """
    def get(self, request):
        show_all = request.query_params.get('all', 'false').lower() == 'true'

        try:
            days = int(request.query_params.get('days', 8))
        except ValueError:
            days = 8

        # Enforce minimum of 8 so spike detection always has a baseline
        days = max(days, 8)

        latest = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        end   = latest.date() if latest else date.today()
        start = end - timedelta(days=days)

        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        type_season    = {}

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            type_season[dtype] = appt.disease.season
            daily_by_dtype[dtype][appt.appointment_datetime.date()] += 1

        results = []
        baseline_days = days - 1  # all days except today

        for dtype in type_season:
            daily_counts = []
            cursor = start
            while cursor <= end:
                daily_counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)

            spike_info = detect_spike(daily_counts, baseline_days=baseline_days)

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

# ─── View 4: Restock Suggestions ─────────────────────────────────────────────

class RestockSuggestionView(APIView):
    """
    GET /api/restock-suggestions/?days=30
    Shows ALL drugs — even those with 0 stock and no recent prescriptions.
    Drugs with 0 stock are always flagged as critical.
    """
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        # ── Step 1: precompute appointment counts per disease type ──
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season   = {}

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            dtype_season[dtype] = appt.disease.season
            daily_by_dtype[dtype][appt.appointment_datetime.date()] += 1

        def build_daily_list(dtype):
            counts = []
            cursor = start
            while cursor <= end:
                counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)
            return counts

        # ── Step 2: stock per drug name (sum all rows) ──
        stock_map = {
            r['drug_name']: r['total_stock']
            for r in DrugMaster.objects
            .values('drug_name')
            .annotate(total_stock=Sum('current_stock'))
        }

        # ── Step 3: avg quantity per drug name from prescription history ──
        avg_qty_map = {
            r['drug__drug_name']: r['avg_qty']
            for r in PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end))
            .values('drug__drug_name')
            .annotate(avg_qty=Avg('quantity'))
        }

        # ── Step 4: disease contributions per drug from prescriptions ──
        drug_disease_map = defaultdict(set)
        lines = (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False
            )
            .select_related('drug', 'disease')
        )
        for line in lines:
            dtype = get_disease_type(line.disease.name)
            drug_disease_map[line.drug.drug_name].add(dtype)

        # ── Step 5: compute demand per disease type ──
        dtype_demand = {}
        for dtype in dtype_season:
            daily = build_daily_list(dtype)
            forecast = moving_average_forecast(daily)
            trend    = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw     = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        # ── Step 6: loop over ALL unique drug names (not just prescribed ones) ──
        all_drug_names = list(stock_map.keys())
        results = []

        for drug_name in all_drug_names:
            current_stock = stock_map.get(drug_name, 0)
            avg_qty       = avg_qty_map.get(drug_name, 1.5) or 1.5
            contributing  = list(drug_disease_map.get(drug_name, set()))

            # If no disease contribution found, use all active disease types
            if not contributing:
                contributing = list(dtype_demand.keys())

            # Combine demand from all contributing diseases
            disease_demands = [
                {
                    'predicted_demand': dtype_demand[d]['demand'],
                    'seasonal_weight':  dtype_demand[d]['seasonal_weight']
                }
                for d in contributing if d in dtype_demand
            ]

            combined_demand = apply_multi_disease_contribution(disease_demands) if disease_demands else 0.0

            # ── Key fix: if stock is 0, always mark as critical ──
            if current_stock == 0:
                results.append({
                    'drug_name':             drug_name,
                    'generic_name':          _get_generic(drug_name),
                    'current_stock':         0,
                    'predicted_demand':      round(combined_demand * avg_qty * 1.2, 2),
                    'suggested_restock':     max(1, int(combined_demand * avg_qty * 1.2)),
                    'status':                'critical',
                    'contributing_diseases': contributing[:8],
                })
            else:
                suggestion = calculate_restock(
                    drug_name=drug_name,
                    generic_name=_get_generic(drug_name),
                    predicted_demand=combined_demand,
                    avg_quantity_per_prescription=avg_qty,
                    current_stock=current_stock,
                    contributing_diseases=contributing[:8]
                )
                results.append(suggestion)

        # Sort: critical first, then low, then sufficient, then by restock qty
        status_order = {'critical': 0, 'low': 1, 'sufficient': 2}
        results.sort(key=lambda x: (
            status_order.get(x['status'], 3),
            -x['suggested_restock']
        ))

        serializer = RestockSuggestionSerializer(results, many=True)
        return Response(serializer.data)


# ─── View 5: CSV Export ───────────────────────────────────────────────────────

# ─── Export View 1: Disease Trends CSV ───────────────────────────────────────

class ExportDiseaseTrendsView(APIView):
    """
    GET /api/export/disease-trends/?days=30
    Downloads disease trend report as CSV.
    """
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="disease_trends_{end}.csv"'
        )
        writer = csv.writer(response)

        # Header
        writer.writerow([
            'Disease', 'Season', 'Category', 'Severity',
            'Total Cases', 'Recent Cases (7d)', 'Older Cases',
            'Trend Score', 'Seasonal Weight', 'Status',
            'Period Start', 'Period End'
        ])

        # Build data
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        type_data = defaultdict(lambda: {
            'season': 'All', 'category': '', 'severity': 1,
            'recent': 0, 'older': 0
        })

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            type_data[dtype]['season']    = appt.disease.season
            type_data[dtype]['category']  = appt.disease.category or ''
            type_data[dtype]['severity']  = appt.disease.severity
            d = appt.appointment_datetime.date()
            if d > mid:
                type_data[dtype]['recent'] += 1
            else:
                type_data[dtype]['older'] += 1

        rows = []
        for dtype, data in type_data.items():
            sw    = get_seasonal_weight(data['season'], current_month)
            score = round(
                weighted_trend_score(data['recent'], data['older']) * sw, 2
            )
            total  = data['recent'] + data['older']
            status = 'High' if score > 50 else 'Moderate' if score > 20 else 'Low'
            rows.append((dtype, data['season'], data['category'], data['severity'],
                         total, data['recent'], data['older'],
                         score, sw, status, start, end))

        rows.sort(key=lambda x: x[7], reverse=True)
        for row in rows:
            writer.writerow(row)

        return response


# ─── Export View 2: Spike Alerts CSV ─────────────────────────────────────────

class ExportSpikeAlertsView(APIView):
    """
    GET /api/export/spike-alerts/?days=8
    Downloads spike alert report as CSV.
    """
    def get(self, request):
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

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="spike_alerts_{end}.csv"'
        )
        writer = csv.writer(response)

        # Header
        writer.writerow([
            'Disease', 'Season', 'Today Count',
            'Period Count', 'Mean (baseline)',
            'Std Dev', 'Threshold',
            'Is Spike', 'Severity',
            'Baseline Days', 'As Of Date'
        ])

        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        type_season    = {}
        type_severity  = {}
        type_category  = {}

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            type_season[dtype]   = appt.disease.season
            type_severity[dtype] = appt.disease.severity
            daily_by_dtype[dtype][appt.appointment_datetime.date()] += 1

        baseline_days = days - 1
        rows = []

        for dtype in type_season:
            daily_counts = []
            cursor = start
            while cursor <= end:
                daily_counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)

            spike_info   = detect_spike(daily_counts, baseline_days=baseline_days)
            period_count = sum(daily_counts)

            rows.append([
                dtype,
                type_season[dtype],
                spike_info['today_count'],
                period_count,
                spike_info['mean_last_7_days'],
                spike_info['std_dev'],
                spike_info['threshold'],
                'YES' if spike_info['is_spike'] else 'no',
                type_severity.get(dtype, 1),
                baseline_days,
                end,
            ])

        # Spikes first, then by today_count desc
        rows.sort(key=lambda x: (0 if x[7] == 'YES' else 1, -x[2]))
        for row in rows:
            writer.writerow(row)

        return response


# ─── Export View 3: Restock Suggestions CSV (detailed per drug row) ──────────

class ExportRestockView(APIView):
    """
    GET /api/export/restock/?days=30
    Downloads detailed restock report — one row per DrugMaster record
    showing drug_strength, dosage_type, clinic_name, current_stock,
    suggested_restock, status.
    """
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="restock_suggestions_{end}.csv"'
        )
        writer = csv.writer(response)

        # Header — detailed per drug row
        writer.writerow([
            'Drug Name', 'Generic Name', 'Drug Strength', 'Dosage Type',
            'Clinic Name', 'Clinic District',
            'Current Stock', 'Predicted Demand',
            'Suggested Restock', 'Status',
            'Contributing Diseases', 'Period'
        ])

        # ── Build appointment data for demand calculation ──
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season   = {}

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            dtype_season[dtype] = appt.disease.season
            daily_by_dtype[dtype][appt.appointment_datetime.date()] += 1

        def build_daily_list(dtype):
            counts = []
            cursor = start
            while cursor <= end:
                counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)
            return counts

        # Pre-compute demand per disease type
        dtype_demand = {}
        for dtype in dtype_season:
            daily    = build_daily_list(dtype)
            forecast = moving_average_forecast(daily)
            trend    = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw     = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        # Disease contributions per drug name
        drug_disease_map = defaultdict(set)
        lines = (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False
            )
            .select_related('drug', 'disease')
        )
        for line in lines:
            dtype = get_disease_type(line.disease.name)
            drug_disease_map[line.drug.drug_name].add(dtype)

        # Avg qty per drug name
        avg_qty_map = {
            r['drug__drug_name']: r['avg_qty']
            for r in PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end))
            .values('drug__drug_name')
            .annotate(avg_qty=Avg('quantity'))
        }

        # ── Extract district from clinic address ──
        def extract_district(address: str) -> str:
            """
            Address format: No.X, street, area, town, District, Tamil Nadu - PIN. Ph: X
            District is the 5th comma-separated segment.
            """
            if not address:
                return 'Unknown'
            parts = [p.strip() for p in address.split(',')]
            if len(parts) >= 5:
                return parts[4].strip()
            return 'Unknown'

        # ── Loop over every single DrugMaster row (detailed) ──
        all_drugs = (
            DrugMaster.objects
            .select_related('clinic')
            .order_by('drug_name', 'clinic__clinic_name', 'drug_strength')
        )

        STATUS_ORDER = {'critical': 0, 'low': 1, 'sufficient': 2}
        rows = []

        for drug in all_drugs:
            drug_name     = drug.drug_name
            current_stock = drug.current_stock or 0
            avg_qty       = avg_qty_map.get(drug_name, 1.5) or 1.5
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

            expected_demand = round(combined * avg_qty * 1.2, 2)

            # Status logic
            if current_stock == 0:
                suggested = max(1, int(expected_demand))
                status    = 'critical'
            else:
                suggested = max(0, int(expected_demand - current_stock))
                if suggested == 0:
                    status = 'sufficient'
                else:
                    shortage_pct = (
                        (expected_demand - current_stock) / expected_demand * 100
                        if expected_demand > 0 else 100
                    )
                    status = 'critical' if shortage_pct > 50 else 'low'

            clinic_name     = drug.clinic.clinic_name if drug.clinic else 'Unknown'
            clinic_district = extract_district(
                drug.clinic.clinic_address_1 if drug.clinic else ''
            )

            rows.append([
                drug_name,
                drug.generic_name or '',
                drug.drug_strength or '',
                drug.dosage_type or '',
                clinic_name,
                clinic_district,
                current_stock,
                expected_demand,
                suggested,
                status,
                ', '.join(contributing[:5]),
                f'{start} to {end}',
            ])

        # Sort: critical first → by drug name → by clinic
        rows.sort(key=lambda x: (
            STATUS_ORDER.get(x[9], 3),
            x[0],
            x[4]
        ))

        for row in rows:
            writer.writerow(row)

        return response


# ─── Keep original combined export for backward compatibility ────────────────

class ExportReportView(APIView):
    """
    GET /api/export-report/
    Original combined CSV — kept for backward compatibility.
    For separate files use /api/export/disease-trends/,
    /api/export/spike-alerts/, /api/export/restock/
    """
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

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

        # ── Build demand data ──────────────────────────────────────
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )
        daily_by_dtype = defaultdict(lambda: defaultdict(int))

        # Total number of active clinics — used to prorate system demand per clinic
        total_clinics = Clinic.objects.count() or 1

        dtype_season   = {}
        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            dtype_season[dtype] = appt.disease.season
            daily_by_dtype[dtype][appt.appointment_datetime.date()] += 1

        def build_daily_list(dtype):
            counts = []
            cursor = start
            while cursor <= end:
                counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)
            return counts

        dtype_demand = {}
        for dtype in dtype_season:
            daily    = build_daily_list(dtype)
            forecast = moving_average_forecast(daily)
            trend    = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw     = get_seasonal_weight(dtype_season[dtype], current_month)
            dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}

        drug_disease_map = defaultdict(set)
        for line in PrescriptionLine.objects.filter(
            prescription__prescription_date__range=(start, end),
            disease__isnull=False
        ).select_related('drug', 'disease'):
            dtype = get_disease_type(line.disease.name)
            drug_disease_map[line.drug.drug_name].add(dtype)

        avg_qty_map = {
            r['drug__drug_name']: r['avg_qty']
            for r in PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end))
            .values('drug__drug_name')
            .annotate(avg_qty=Avg('quantity'))
        }

        def extract_district(address):
            if not address:
                return 'Unknown'
            parts = [p.strip() for p in address.split(',')]
            return parts[4].strip() if len(parts) >= 5 else 'Unknown'

        # ── Group by drug_name + drug_strength + dosage_type + clinic ──
        # This gives one meaningful row per unique drug variant per clinic
        from django.db.models import Sum as DSum

        grouped = (
            DrugMaster.objects
            .select_related('clinic')
            .values(
                'drug_name', 'generic_name',
                'drug_strength', 'dosage_type',
                'clinic__id', 'clinic__clinic_name', 'clinic__clinic_address_1'
            )
            .annotate(total_stock=DSum('current_stock'))
            .order_by('drug_name', 'clinic__clinic_name', 'drug_strength')
        )

        STATUS_ORDER = {'critical': 0, 'low': 1, 'sufficient': 2}
        rows = []

        for g in grouped:
            drug_name     = g['drug_name']
            current_stock = g['total_stock'] or 0
            avg_qty       = avg_qty_map.get(drug_name, 1.5) or 1.5
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
            combined        = apply_multi_disease_contribution(disease_demands) if disease_demands else 0.0
            expected_demand = round(combined * avg_qty * 1.2, 2)

            # Prorate demand per clinic
            per_clinic_demand = round(combined / total_clinics * avg_qty * 1.2, 2)

            if current_stock == 0:
                suggested = max(1, int(per_clinic_demand))
                status    = 'critical'
            else:
                suggested = max(0, int(per_clinic_demand - current_stock))
                if suggested == 0:
                    status = 'sufficient'
                else:
                    pct = (per_clinic_demand - current_stock) / per_clinic_demand * 100 if per_clinic_demand > 0 else 100
                    status = 'critical' if pct > 50 else 'low'

            clinic_name     = g['clinic__clinic_name'] or 'Unknown'
            clinic_address  = g['clinic__clinic_address_1'] or ''
            district        = extract_district(clinic_address)

            rows.append([
                drug_name,
                g['generic_name'] or '',
                g['drug_strength'] or '',
                g['dosage_type'] or '',
                clinic_name,
                district,
                current_stock,
                per_clinic_demand,    # ← per clinic, not system total
                suggested,
                status,
                ', '.join(contributing[:5]),
                f'{start} to {end}',
            ])

        rows.sort(key=lambda x: (STATUS_ORDER.get(x[9], 3), x[0], x[4]))
        for row in rows:
            writer.writerow(row)

        return response
