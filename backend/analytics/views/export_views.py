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

from ..ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from ..spike_detector import detect_spike, get_seasonal_weight
from ..restock_calculator import calculate_restock, apply_multi_disease_contribution, calculate_dynamic_safety_buffer
from ..serializers import (
    DiseaseTrendSerializer, TimeSeriesPointSerializer,
    SpikeAlertSerializer, RestockSuggestionSerializer
)
from ..services.medicine_analytics import MedicineAnalyticsService
from ..services.restock_service import RestockService
from ..utils.validators import validate_positive_int

from ..aggregation import (
    aggregate_disease_counts, aggregate_daily_counts, build_daily_list,
    aggregate_medicine_usage, compare_disease_trends, aggregate_top_medicines,
    aggregate_seasonality, aggregate_doctor_wise,
    aggregate_weekly, aggregate_monthly, get_disease_type,
)

from .utils import (
    cache_api_response, GENERIC_MAP, _get_generic, _extract_district,
    _get_db_date_range, _get_date_range, _build_daily_list
)

# export_views.py extracted classes

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
            .filter(prescription_date__range=(start, end), disease__isnull=False)
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
    


# ── New Feature 1: Disease Trend Comparison ───────────────────────────────────



