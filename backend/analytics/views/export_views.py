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
from ..services.restock_calculator import calculate_restock, apply_multi_disease_contribution, calculate_dynamic_safety_buffer
from ..serializers.serializers import (
    DiseaseTrendSerializer, TimeSeriesPointSerializer,
    SpikeAlertSerializer, RestockSuggestionSerializer
)
from ..services.restock_service import RestockService
from ..services.usage import UsageIntelligence
from ..services.forecasting import ForecastingService
from ..utils.validators import validate_positive_int

from ..services.aggregation import (
    aggregate_disease_counts, aggregate_daily_counts, build_daily_list,
    aggregate_medicine_usage, compare_disease_trends, aggregate_top_medicines,
    aggregate_seasonality, aggregate_doctor_wise,
    aggregate_weekly, aggregate_monthly, get_disease_type,
)

from .utils import (
    cache_api_response, _get_db_date_range, _get_date_range, 
    _build_daily_list, apply_clinic_filter
)
from ..utils.chemistry import GENERIC_MAP, _get_generic
from ..utils.geo import _extract_district

# export_views.py extracted classes

class ExportDiseaseTrendsView(APIView):
    """GET /api/export/disease-trends/ — Comparison-based CSV"""
    def get(self, request):
        start, end    = _get_date_range(request)
        days = (end - start).days + 1
        current_month = date.today().month
        
        # Period 1 (Current): start to end
        # Period 2 (Prior): same length before start
        p1_start, p1_end = start, end
        p2_start, p2_end = p1_start - timedelta(days=days), p1_start - timedelta(days=1)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="disease_trends_{end}.csv"'
        writer = csv.writer(response)
        
        writer.writerow([
            'Disease', 'Season', 'Category', 'Severity',
            f'Cases ({days}d Current)', f'Cases ({days}d Previous)', 'Growth %',
            'Trend Status', 'Seasonal Weight', 'Start Date', 'End Date'
        ])

        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')

        appt_qs_base = Appointment.objects.all()
        appt_qs = apply_clinic_filter(appt_qs_base, request).exclude(var_filter)

        results = compare_disease_trends(p2_start, p2_end, p1_start, p1_end, queryset=appt_qs)

        for r in results:
            # Fetch extra metadata for the row
            d_name = r['disease_name']
            d_obj = Disease.objects.filter(name__icontains=d_name).first()
            season = d_obj.season if d_obj else 'All'
            cat    = d_obj.category if d_obj else ''
            sev    = d_obj.severity if d_obj else 1
            sw     = get_seasonal_weight(season, current_month)

            writer.writerow([
                d_name, season, cat, sev,
                r['period1_count'], r['period2_count'], f"{r['pct_change']}%",
                r['direction'].upper(), sw, p1_start, p1_end
            ])
            
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

        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')
        qs_base = Appointment.objects.filter(appointment_datetime__date__range=(start, end), disease__isnull=False).exclude(var_filter)
        qs = apply_clinic_filter(qs_base, request) \
            .select_related('disease') \
            .annotate(appt_date=TruncDate('appointment_datetime')) \
            .values('appt_date', 'disease__name', 'disease__season', 'disease__severity') \
            .annotate(day_count=Count('id'))

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

        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')
        # Demand computation (ORM only)
        appt_qs_base = Appointment.objects.filter(appointment_datetime__date__range=(start, end), disease__isnull=False).exclude(var_filter)
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

        disease_case_map = {dtype: sum(dm.values()) for dtype, dm in daily_by_dtype.items()}

        qty_qs_base = PrescriptionLine.objects.filter(prescription_date__range=(start, end), disease__isnull=False).exclude(var_filter | Q(drug__drug_name__icontains='Vari') | Q(drug__drug_name__endswith=' V'))
        qty_qs = apply_clinic_filter(qty_qs_base, request, clinic_field='prescription__clinic') \
            .select_related('drug', 'disease') \
            .values('drug__drug_name', 'disease__name') \
            .annotate(total_qty=Sum('quantity'))

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

        active_drugs = set(avg_usage_map.keys())
        district_filter = request.query_params.get('district') # This is actually the Clinic Name now
        
        grouped_qs = apply_clinic_filter(DrugMaster.objects.select_related('clinic').filter(
            Q(drug_name__in=active_drugs) | Q(current_stock__lt=10)
        ), request)
        
        if district_filter:
            grouped_qs = grouped_qs.filter(clinic__clinic_name__icontains=district_filter.strip())

        grouped = (
            grouped_qs
            .values('drug_name', 'generic_name', 'drug_strength', 'dosage_type',
                    'clinic__clinic_name', 'clinic__clinic_address_1')
            .annotate(
                total_stock=Sum('current_stock'),
                clinic_row_count=Count('id')
            )
            .order_by('total_stock', 'drug_name', 'clinic__clinic_name')
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
            clinic_count    = g['clinic_row_count'] or 1
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

            if suggested > 0 or current_stock == 0:
                district = _extract_district(g['clinic__clinic_address_1'])
                rows.append([
                    drug_name, g['generic_name'] or '', g['drug_strength'] or '',
                    g['dosage_type'] or '', g['clinic__clinic_name'] or '', district,
                    current_stock, district_demand, suggested, status,
                    ', '.join(contributing[:5]), f'{start} to {end}',
                ])
            
            # Capping for performance on massive datasets
            if len(rows) >= 10000:
                break

        rows.sort(key=lambda x: (STATUS_ORDER.get(x[9], 3), x[0], x[4]))
        for row in rows:
            writer.writerow(row)
        return response

class ExportReportView(APIView):
    """
    GET /api/export-report/
    Standardized to honor selected range.
    """
    def get(self, request):
        from ..services.insights_service import InsightsService
        from ..services.forecasting import ForecastingService
        
        start, end = _get_date_range(request)
        days = (end - start).days
        
        service = InsightsService()
        forecasting = ForecastingService()
        insights = service.get_actionable_insights(days=days, request=request)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="intelligent_health_report_{end}.csv"'
        writer = csv.writer(response)
        
        writer.writerow(['DECISION SUPPORT SUMMARY'])
        writer.writerow(['Period', f'{start} to {end}'])
        writer.writerow(['Risk Level', insights['metadata']['risk_level'], 'Buffer', insights['metadata']['safety_buffer']])
        writer.writerow([])
        writer.writerow(['STRATEGIC RECOMMENDATIONS'])
        for rec in insights['recommendations']: writer.writerow([rec])
        writer.writerow([])
        writer.writerow(['ACTIVE ALERTS (Outbreaks & Spikes)'])
        writer.writerow(['Disease', 'Severity', 'Current Cases', 'Expected Normal', 'Status'])
        for o in insights['outbreaks']:
            writer.writerow([o['disease'], o['severity'], o['current_cases'], o['expected_normal'], 'Critical' if o['severity'] == 'Critical' else 'Warning'])
        writer.writerow([])
        writer.writerow(['CRITICAL RESOURCE DEPLETION'])
        writer.writerow(['Drug Name', 'Current Stock', 'Days until Depletion', 'Expected Date'])
        for s in insights['critical_stock']:
            depletion = forecasting.forecast_stock_depletion(s['drug_name'], request=request)
            writer.writerow([s['drug_name'], s['current_stock'], depletion.get('days_until_depletion', 'N/A'), depletion.get('depletion_date', 'N/A')])
        return response


class ExportMedicineUsageView(APIView):
    """GET /api/export/medicine-usage/ — CSV download"""
    def get(self, request):
        start, end = _get_date_range(request)
        disease_name = request.query_params.get('disease', 'All')
        from ..services.usage import UsageIntelligence
        service = UsageIntelligence()
        # Exclude Variants
        var_filter = Q(drug__drug_name__icontains='Vari') | Q(drug__drug_name__endswith=' V')
        rx_qs_base = PrescriptionLine.objects.all()
        rx_qs = apply_clinic_filter(rx_qs_base, request, clinic_field='prescription__clinic').exclude(var_filter)
        data = service.get_medicine_usage_per_disease(
            disease_name=disease_name,
            days=(end - start).days,
            rx_queryset=rx_qs
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="medicine_usage_{end}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Medicine Usage Report', f'Disease: {disease_name}', f'Period: {start} to {end}'])
        writer.writerow([])
        writer.writerow(['Drug Name', 'Generic Name', 'Total Quantity Used', 'Prescription Count'])
        for med in data.get('top_medicines', []):
            writer.writerow([med['drug_name'], med['generic_name'], med['total_quantity'], med['prescription_count']])
        return response


class ExportDoctorTrendsView(APIView):
    """GET /api/export/doctor-trends/ — CSV download"""
    def get(self, request):
        start, end = _get_date_range(request)
        from ..services.usage import UsageIntelligence
        service = UsageIntelligence()
        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')
        appt_qs_base = Appointment.objects.all()
        appt_qs = apply_clinic_filter(appt_qs_base, request).exclude(var_filter)
        data = service.get_doctor_patterns(days=(end - start).days, appt_queryset=appt_qs)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="doctor_trends_{end}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Doctor Activity Report', f'Period: {start} to {end}'])
        writer.writerow([])
        writer.writerow(['Doctor Name', 'Primary Disease Type', 'Total Consultations'])
        for doc in data:
            writer.writerow([doc['doctor_name'], doc['top_specialization'], doc['total_cases']])
        return response


class ExportWeeklyReportView(APIView):
    """GET /api/export/reports/weekly/ — Simplified WTD/Range CSV"""
    def get(self, request):
        start, end = _get_date_range(request)
        from .report_views import WeeklyReportView
        # Exclude Variants in the underlying view search
        report_data = WeeklyReportView().get(request).data
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="weekly_report_{end}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Weekly Disease Case Report', f'Period: {start} to {end}'])
        writer.writerow([])
        writer.writerow(['Week Label', 'Start', 'End', 'Total Cases', 'Disease Breakdown'])
        for w in report_data.get('weeks', []):
            diseases = "; ".join([f"{d['disease_name']}: {d['case_count']} ({d['percentage']}%)" for d in w['diseases']])
            writer.writerow([w['week_label'], w['week_start'], w['week_end'], w['total_cases'], diseases])
        return response


class ExportMonthlyReportView(APIView):
    """GET /api/export/reports/monthly/ — Simplified MTD/Range CSV"""
    def get(self, request):
        start, end = _get_date_range(request)
        from .report_views import MonthlyReportView
        # Exclude Variants in the underlying view search
        report_data = MonthlyReportView().get(request).data
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="monthly_report_{end}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Monthly Disease Case Report', f'Period: {start} to {end}'])
        writer.writerow([])
        writer.writerow(['Month', 'Total Cases', 'Disease Breakdown'])
        for m in report_data.get('months', []):
            diseases = "; ".join([f"{d['disease_name']}: {d['case_count']} ({d['percentage']}%)" for d in m['diseases']])
            writer.writerow([m['month_label'], m['total_cases'], diseases])
        return response
class ExportLowStockAlertView(APIView):
    """GET /api/export/low-stock-alerts/?threshold=50"""
    def get(self, request):
        try:
            threshold = int(request.query_params.get('threshold', 50))
        except ValueError:
            threshold = 50

        from django.db.models import Avg, Sum, Count
        stock_qs_base = DrugMaster.objects.all()
        stock_qs = apply_clinic_filter(stock_qs_base, request) \
            .values('drug_name', 'generic_name') \
            .annotate(
                avg_stock=Avg('current_stock'),
                total_stock=Sum('current_stock'),
                clinic_count=Count('clinic', distinct=True),
            ) \
            .filter(avg_stock__isnull=False, avg_stock__lte=threshold) \
            .order_by('avg_stock')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="low_stock_alerts_{date.today()}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Low Stock Alert Report', f'Threshold: {threshold}', f'Generated: {date.today()}'])
        writer.writerow(['Drug Name', 'Generic Name', 'Avg Stock/Clinic', 'Total Stock', 'Clinics Count', 'Threshold', 'Alert Level'])

        for row in stock_qs:
            avg = round(row['avg_stock'] or 0, 1)
            if avg == 0: alert_level = 'OUT OF STOCK'
            elif avg <= threshold * 0.25: alert_level = 'CRITICAL'
            elif avg <= threshold * 0.5: alert_level = 'LOW'
            else: alert_level = 'WARNING'

            writer.writerow([
                row['drug_name'], row['generic_name'] or '', avg,
                row['total_stock'], row['clinic_count'], threshold, alert_level
            ])
        return response


class ExportMedicineDependencyView(APIView):
    """GET /api/export/medicine-dependency/?days=30&disease=Flu"""
    def get(self, request):
        days = validate_positive_int(request.query_params.get('days'), 'days', default=30)
        disease_name = request.query_params.get('disease')
        
        service = UsageIntelligence()
        rx_qs_base = PrescriptionLine.objects.all()
        rx_qs = apply_clinic_filter(rx_qs_base, request, clinic_field='prescription__clinic')

        if not disease_name or disease_name.lower() == 'all':
            data = service.get_all_medicine_dependencies(days=days, rx_queryset=rx_qs)
            filename = f"medicine_dependencies_all_{date.today()}.csv"
            title = "All Medicine Dependencies"
        else:
            data = service.get_medicine_usage_per_disease(disease_name=disease_name, days=days, rx_queryset=rx_qs)
            filename = f"medicine_dependency_{disease_name.replace(' ', '_')}_{date.today()}.csv"
            title = f"Medicine Dependency: {disease_name}"

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow([title, f'Period: Last {days} days', f'Generated: {date.today()}'])
        writer.writerow([])
        # Structure differs if it's all vs single
        if not disease_name or disease_name.lower() == 'all':
            # all_medicine_dependencies returns a list of dictionaries (one per disease)
            writer.writerow(['Disease Name', 'Total Prescriptions', 'Unique Medicines Count', 'Top Medicine', 'Medicine Prescription Count'])
            for disease in data:
                # For "all", we list each disease and its primary dependency
                top_med = disease['medicines'][0] if disease['medicines'] else {}
                writer.writerow([
                    disease['disease_name'], 
                    disease['total_prescriptions'], 
                    disease['unique_medicines'],
                    top_med.get('drug_name', 'N/A'),
                    top_med.get('prescriptions', 0)
                ])
                # Optionally list other medicines in next rows or same row
        else:
            # get_medicine_usage_per_disease returns {top_medicines: [...]}
            writer.writerow(['Drug Name', 'Generic Name', 'Total Quantity', 'Prescription Count'])
            for item in data.get('top_medicines', []):
                writer.writerow([
                    item.get('drug_name'), 
                    item.get('generic_name'), 
                    item.get('total_quantity'), 
                    item.get('prescription_count')
                ])
        
        return response


class ExportStockDepletionView(APIView):
    """GET /api/export/stock-depletion/?drug_name=Flu&days=30"""
    def get(self, request):
        selected_drug = request.query_params.get('drug_name')
        days = validate_positive_int(request.query_params.get('days'), 'days', default=30)
        
        service = ForecastingService()
        rx_qs_base = PrescriptionLine.objects.all()
        rx_qs = apply_clinic_filter(rx_qs_base, request, clinic_field='prescription__clinic')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="stock_depletion_report_{date.today()}.csv"'
        writer = csv.writer(response)

        if selected_drug and selected_drug.lower() != 'all':
            # Single drug detailed view (original logic)
            result = service.forecast_stock_depletion(drug_name=selected_drug, days=days, rx_queryset=rx_qs, request=request)
            writer.writerow(['Stock Depletion Detail', f'Drug: {selected_drug}', f'Period: {days} days'])
            writer.writerow([])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Drug Name', result.get('drug_name')])
            writer.writerow(['Generic Name', result.get('generic_name')])
            writer.writerow(['Current Stock', result.get('current_stock', 0)])
            writer.writerow(['Avg Daily Usage', result.get('avg_daily_usage', 0)])
            writer.writerow(['Days Until Depletion', result.get('days_until_depletion', 'N/A')])
            writer.writerow(['Estimated Depletion Date', result.get('depletion_date', 'N/A')])
            writer.writerow(['Status', result.get('status', 'Unknown')])
        else:
            # Bulk export view for ALL drugs
            writer.writerow(['System-wide Stock Depletion Forecast', f'Generated: {date.today()}', f'Period: {days} days'])
            writer.writerow([])
            writer.writerow(['Drug Name', 'Generic Name', 'Current Stock', 'Avg Daily Usage', 'Days Left', 'Depletion Date', 'Status'])
            
            # Optimization: Get all unique drug names with stock or usage
            relevant_drugs = DrugMaster.objects.filter(current_stock__gt=0).values_list('drug_name', flat=True).distinct()
            # Also include drugs used recently
            usage_drugs = rx_qs.filter(prescription_date__gte=date.today()-timedelta(days=days)).values_list('drug__drug_name', flat=True).distinct()
            
            all_drugs = sorted(set(relevant_drugs) | set(usage_drugs))
            
            for dname in all_drugs:
                res = service.forecast_stock_depletion(drug_name=dname, days=days, rx_queryset=rx_qs, request=request)
                if not res.get('error'):
                    writer.writerow([
                        res.get('drug_name'), res.get('generic_name'), 
                        res.get('current_stock'), res.get('avg_daily_usage'),
                        res.get('days_until_depletion'), res.get('depletion_date'),
                        res.get('status')
                    ])
                
        return response


