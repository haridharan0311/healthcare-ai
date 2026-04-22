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

# report_views.py extracted classes

class WeeklyReportView(APIView):
    """
    GET /api/reports/weekly/?days=60

    Returns one box per week. Each box contains:
      week_label, week_start, week_end, total_cases,
      diseases: [{disease_name, case_count, percentage}]

    Range options: 1M=30d, 2M=60d, 3M=90d, 4M=120d, 6M=180d, 9M=270d, 1Y=365d, 2Y=730d
    """
    def get(self, request):
        start, end = _get_date_range(request)

        # ORM: TruncWeek groups by week start date
        appt_qs_base = Appointment.objects.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')
        qs = apply_clinic_filter(appt_qs_base, request).exclude(var_filter) \
            .select_related('disease') \
            .annotate(week_start=TruncWeek('appointment_datetime')) \
            .values('week_start', 'disease__name') \
            .annotate(case_count=Count('id')) \
            .order_by('week_start', '-case_count')

        # Group by week
        week_map = defaultdict(lambda: defaultdict(int))
        for row in qs:
            ws    = str(row['week_start'])[:10] if row['week_start'] else 'Unknown'
            dtype = get_disease_type(row['disease__name'])
            week_map[ws][dtype] += row['case_count']

        # Build boxes
        weeks = []
        for i, (week_start, type_counts) in enumerate(sorted(week_map.items())):
            total = sum(type_counts.values())
            # Calculate week end
            from datetime import datetime
            try:
                ws_date  = datetime.strptime(week_start, '%Y-%m-%d').date()
                we_date  = ws_date + timedelta(days=6)
                week_end = str(we_date)
                week_label = f'Week {i + 1} ({ws_date.strftime("%d %b")} – {we_date.strftime("%d %b %Y")})'
            except Exception:
                week_end   = week_start
                week_label = f'Week {i + 1}'

            sorted_diseases = sorted(type_counts.items(), key=lambda x: -x[1])
            weeks.append({
                'week_number': i + 1,
                'week_label':  week_label,
                'week_start':  week_start,
                'week_end':    week_end,
                'total_cases': total,
                'diseases': [
                    {
                        'disease_name': d,
                        'case_count':   c,
                        'percentage':   round(c / total * 100, 1) if total > 0 else 0,
                    }
                    for d, c in sorted_diseases
                ],
            })

        return Response({
            'period':      f'{start} to {end}',
            'total_weeks': len(weeks),
            'weeks':       weeks,
        })


# ─── Monthly Report ───────────────────────────────────────────────────────────



class MonthlyReportView(APIView):
    """
    GET /api/reports/monthly/?days=365

    Returns one box per month. Same structure as weekly.

    Range options: 3M=90d, 6M=180d, 1Y=365d, 2Y=730d, 3Y=1095d, 4Y=1460d, 5Y=1825d
    """
    def get(self, request):
        start, end = _get_date_range(request)

        appt_qs_base = Appointment.objects.filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')
        qs = apply_clinic_filter(appt_qs_base, request).exclude(var_filter) \
            .select_related('disease') \
            .annotate(month_start=TruncMonth('appointment_datetime')) \
            .values('month_start', 'disease__name') \
            .annotate(case_count=Count('id')) \
            .order_by('month_start', '-case_count')

        month_map = defaultdict(lambda: defaultdict(int))
        for row in qs:
            ms    = str(row['month_start'])[:7] if row['month_start'] else 'Unknown'
            dtype = get_disease_type(row['disease__name'])
            month_map[ms][dtype] += row['case_count']

        months = []
        for i, (month_key, type_counts) in enumerate(sorted(month_map.items())):
            total = sum(type_counts.values())
            try:
                from datetime import datetime
                m_date     = datetime.strptime(month_key, '%Y-%m')
                month_label = m_date.strftime('%B %Y')
            except Exception:
                month_label = month_key

            sorted_diseases = sorted(type_counts.items(), key=lambda x: -x[1])
            months.append({
                'month_number': i + 1,
                'month_label':  month_label,
                'month_key':    month_key,
                'total_cases':  total,
                'diseases': [
                    {
                        'disease_name': d,
                        'case_count':   c,
                        'percentage':   round(c / total * 100, 1) if total > 0 else 0,
                    }
                    for d, c in sorted_diseases
                ],
            })

        return Response({
            'period':       f'{start} to {end}',
            'total_months': len(months),
            'months':       months,
        })

# ── New Feature 7: Auto Safety Buffer in Restock ─────────────────────────────
# Integrated inside RestockSuggestionView — spike_count drives the buffer.
# Add this block inside RestockSuggestionView.get() before the results loop:
#
#   spike_results = [
#       detect_spike(_build_daily_list(daily_by_dtype, d, start, end))
#       for d in dtype_season
#   ]
#   spike_count   = sum(1 for s in spike_results if s['is_spike'])
#   safety_buffer = calculate_dynamic_safety_buffer(spike_count, len(dtype_season))
#
# Then pass safety_buffer= to calculate_restock().



class TodaySummaryView(APIView):
    """
    GET /api/today-summary/
    Returns counts for today based on latest DB date.
    No date param — always uses latest appointment date in DB.
    
    IMPORTANT: Only counts appointments with a disease assigned for consistency
    with SpikeAlertView and WhatChangedTodayView. This ensures the dashboard
    shows consistent case counts across all sections.
    """
    @cache_api_response(timeout=300)  # Cache for 30 seconds to match frontend refresh
    def get(self, request):
        # Latest date in DB
        latest = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        today = latest.date() if latest else date.today()

        # Per disease today — ORM Count, no loops
        # Only count appointments with a disease assigned for consistency with other views
        appt_qs_base = Appointment.objects.filter(
            appointment_datetime__date=today,
            disease__isnull=False,
        )
        # Exclude Variants
        var_filter = Q(disease__name__icontains='Vari') | Q(disease__name__endswith=' V')
        disease_today = apply_clinic_filter(appt_qs_base, request).exclude(var_filter) \
            .select_related('disease') \
            .values('disease__name') \
            .annotate(cnt=Count('id'))

        # Total appointments today (with disease assigned)
        today_count = sum(row['cnt'] for row in disease_today)

        # Group by disease type
        by_type = defaultdict(int)
        for row in disease_today:
            dtype = get_disease_type(row['disease__name'])
            by_type[dtype] += row['cnt']

        return Response({
            'date':           str(today),
            'total_today':    today_count,
            'by_disease':     [
                {'disease': k, 'count': v}
                for k, v in sorted(by_type.items(), key=lambda x: -x[1])
            ],
        })




class WhatChangedTodayView(APIView):
    """
    GET /api/what-changed-today/
    FEATURE 10: Summarizes daily changes like spikes, risks, and trend shifts.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        from ..services.insights_service import InsightsService
        service = InsightsService()
        
        # Get actionable insights for the last 30 days
        insights = service.get_actionable_insights(days=30, request=request)
        
        # Add today's specific stats
        latest = Appointment.objects.aggregate(latest=Max('appointment_datetime'))['latest']
        today = latest.date() if latest else date.today()
        
        today_count = Appointment.objects.filter(
            appointment_datetime__date=today,
            disease__isnull=False
        ).count()
        
        return Response({
            'date': str(today),
            'total_appointments': today_count,
            'summary': insights['recommendations'],
            'risks': {
                'outbreaks': insights['outbreaks'],
                'critical_stock': insights['critical_stock']
            },
            'trends': {
                'rising_diseases': insights['rising_trends']
            }
        })




