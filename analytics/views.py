import csv
from datetime import date, timedelta
from collections import defaultdict

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
            if spike_info['is_spike'] or show_all:
                results.append({
                    'disease_name': dtype,
                    **spike_info
                })

        results.sort(key=lambda x: x['today_count'], reverse=True)
        serializer = SpikeAlertSerializer(results, many=True)
        return Response(serializer.data)

# ─── View 4: Restock Suggestions ─────────────────────────────────────────────

class RestockSuggestionView(APIView):
    """
    GET /api/restock-suggestions/?days=30
    Groups by drug name + disease TYPE (not individual disease row).
    """
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        # Precompute appointment counts per disease type
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype = defaultdict(lambda: defaultdict(int))
        dtype_season = {}

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

        # Avg quantity per drug name
        avg_qty_map = {
            r['drug__drug_name']: r['avg_qty']
            for r in PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end))
            .values('drug__drug_name')
            .annotate(avg_qty=Avg('quantity'))
        }

        # Sum total stock across all DrugMaster rows with same drug_name
        stock_map = {
            r['drug_name']: r['total_stock']
            for r in DrugMaster.objects
            .values('drug_name')
            .annotate(total_stock=Sum('current_stock'))
        }

        # Single loop — build drug_name → disease demands
        drug_results = defaultdict(lambda: {
            'generic_name': '',
            'current_stock': 0,
            'disease_demands': [],
            'seen_diseases': set(),
        })

        lines = (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False
            )
            .select_related('drug', 'disease')
        )

        for line in lines:
            drug_name = line.drug.drug_name
            dtype = get_disease_type(line.disease.name)

            entry = drug_results[drug_name]

            # Set drug meta once
            if not entry['generic_name']:
                entry['generic_name'] = line.drug.generic_name or ''
                entry['current_stock'] = stock_map.get(line.drug.drug_name, 0)

            # Add disease contribution only once per disease type
            if dtype not in entry['seen_diseases']:
                entry['seen_diseases'].add(dtype)

                daily = build_daily_list(dtype)
                forecast = moving_average_forecast(daily)
                trend = weighted_trend_score(
                    sum(daily[-7:]),
                    sum(daily[:-7]) if len(daily) > 7 else 0
                )
                demand = predict_demand(trend, forecast)
                sw = get_seasonal_weight(
                    dtype_season.get(dtype, 'All'), current_month
                )

                entry['disease_demands'].append({
                    'disease_name': dtype,
                    'predicted_demand': demand,
                    'seasonal_weight': sw,
                })

        # Build final restock list
        results = []
        for drug_name, data in drug_results.items():
            combined = apply_multi_disease_contribution(data['disease_demands'])
            avg_qty = avg_qty_map.get(drug_name, 1.0) or 1.0
            contributing = list(data['seen_diseases'])

            suggestion = calculate_restock(
                drug_name=drug_name,
                generic_name=data['generic_name'],
                predicted_demand=combined,
                avg_quantity_per_prescription=avg_qty,
                current_stock=data['current_stock'],
                contributing_diseases=contributing
            )
            results.append(suggestion)

        results.sort(key=lambda x: x['suggested_restock'], reverse=True)
        serializer = RestockSuggestionSerializer(results, many=True)
        return Response(serializer.data)


# ─── View 5: CSV Export ───────────────────────────────────────────────────────

class ExportReportView(APIView):
    def get(self, request):
        start, end = _get_date_range(request)
        current_month = date.today().month
        mid = end - timedelta(days=7)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="health_report_{end}.csv"'
        )
        writer = csv.writer(response)

        # ── Build shared appointment data (used by all 3 sections) ──
        appts = (
            Appointment.objects
            .filter(appointment_datetime__date__range=(start, end))
            .select_related('disease')
        )

        daily_by_dtype  = defaultdict(lambda: defaultdict(int))
        dtype_season    = {}
        dtype_recent    = defaultdict(int)
        dtype_older     = defaultdict(int)

        for appt in appts:
            if not appt.disease:
                continue
            dtype = get_disease_type(appt.disease.name)
            dtype_season[dtype] = appt.disease.season
            d = appt.appointment_datetime.date()
            daily_by_dtype[dtype][d] += 1
            if d > mid:
                dtype_recent[dtype] += 1
            else:
                dtype_older[dtype] += 1

        def build_daily_list(dtype):
            counts = []
            cursor = start
            while cursor <= end:
                counts.append(daily_by_dtype[dtype].get(cursor, 0))
                cursor += timedelta(days=1)
            return counts

        # ── Section 1: Disease Trends ──
        writer.writerow([])
        writer.writerow(['DISEASE TREND REPORT', f'Period: {start} to {end}'])
        writer.writerow(['Disease', 'Season', 'Total Cases',
                         'Trend Score', 'Seasonal Weight', 'Status'])

        trend_rows = []
        for dtype, season in dtype_season.items():
            sw = get_seasonal_weight(season, current_month)
            score = round(weighted_trend_score(dtype_recent[dtype], dtype_older[dtype]) * sw, 2)
            total = dtype_recent[dtype] + dtype_older[dtype]
            status = 'High' if score > 50 else 'Moderate' if score > 20 else 'Low'
            trend_rows.append((dtype, season, total, score, sw, status))

        trend_rows.sort(key=lambda x: x[3], reverse=True)
        for row in trend_rows:
            writer.writerow(row)

        # ── Section 2: Spike Alerts ──
        writer.writerow([])
        writer.writerow(['SPIKE ALERTS', f'As of: {end}'])
        writer.writerow(['Disease', 'Today Count', 'Mean (7d)',
                         'Std Dev', 'Threshold', 'Spike?'])

        for dtype in dtype_season:
            daily = build_daily_list(dtype)
            s = detect_spike(daily)
            writer.writerow([
                dtype, s['today_count'], s['mean_last_7_days'],
                s['std_dev'], s['threshold'],
                'YES' if s['is_spike'] else 'no'
            ])

        # ── Section 3: Restock Suggestions ──
        writer.writerow([])
        writer.writerow(['RESTOCK SUGGESTIONS'])
        writer.writerow(['Drug', 'Generic Name', 'Current Stock',
                         'Predicted Demand', 'Suggested Restock',
                         'Status', 'Contributing Diseases'])

        lines = (
            PrescriptionLine.objects
            .filter(
                prescription__prescription_date__range=(start, end),
                disease__isnull=False
            )
            .select_related('drug', 'disease')
        )

        avg_qty_qs = (
            PrescriptionLine.objects
            .filter(prescription__prescription_date__range=(start, end))
            .values('drug__drug_name')
            .annotate(avg_qty=Avg('quantity'))
        )
        avg_qty_map = {r['drug__drug_name']: r['avg_qty'] for r in avg_qty_qs}

        stock_map = {
            r['drug_name']: r['total_stock']
            for r in DrugMaster.objects
            .values('drug_name')
            .annotate(total_stock=Sum('current_stock'))
        }

        drug_results = defaultdict(lambda: {
            'generic_name': '', 'current_stock': 0, 'disease_demands': []
        })
        seen = set()

        for line in lines:
            drug_name = line.drug.drug_name
            dtype = get_disease_type(line.disease.name)
            key = (drug_name, dtype)
            if key in seen:
                continue
            seen.add(key)

            daily = build_daily_list(dtype)
            forecast = moving_average_forecast(daily)
            trend = weighted_trend_score(
                sum(daily[-7:]),
                sum(daily[:-7]) if len(daily) > 7 else 0
            )
            demand = predict_demand(trend, forecast)
            sw = get_seasonal_weight(line.disease.season, current_month)

            drug_results[drug_name]['generic_name'] = line.drug.generic_name or ''
            drug_results[drug_name]['current_stock'] = stock_map.get(line.drug.drug_name, 0)
            drug_results[drug_name]['disease_demands'].append({
                'disease_name': dtype,
                'predicted_demand': demand,
                'seasonal_weight': sw,
            })

        restock_rows = []
        for drug_name, data in drug_results.items():
            combined = apply_multi_disease_contribution(data['disease_demands'])
            avg_qty = avg_qty_map.get(drug_name, 1.0) or 1.0
            contributing = list({d['disease_name'] for d in data['disease_demands']})
            s = calculate_restock(
                drug_name, data['generic_name'], combined,
                avg_qty, data['current_stock'], contributing
            )
            restock_rows.append(s)

        restock_rows.sort(key=lambda x: x['suggested_restock'], reverse=True)
        for s in restock_rows:
            writer.writerow([
                s['drug_name'], s['generic_name'], s['current_stock'],
                s['predicted_demand'], s['suggested_restock'],
                s['status'], ', '.join(s['contributing_diseases'])
            ])

        return response
