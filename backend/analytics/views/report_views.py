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
        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('disease')
            .annotate(week_start=TruncWeek('appointment_datetime'))
            .values('week_start', 'disease__name')
            .annotate(case_count=Count('id'))
            .order_by('week_start', '-case_count')
        )

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

        qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start, end),
                disease__isnull=False,
            )
            .select_related('disease')
            .annotate(month_start=TruncMonth('appointment_datetime'))
            .values('month_start', 'disease__name')
            .annotate(case_count=Count('id'))
            .order_by('month_start', '-case_count')
        )

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
        disease_today = (
            Appointment.objects
            .filter(
                appointment_datetime__date=today,
                disease__isnull=False,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(cnt=Count('id'))
        )

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

    Summarizes today’s key changes: appointments, spike alerts, stock risks,
    and fast-moving disease trends.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        latest = Appointment.objects.aggregate(latest=Max('appointment_datetime'))['latest']
        today = latest.date() if latest else date.today()

        # Today counts by disease type
        today_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date=today,
                disease__isnull=False,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(cnt=Count('id'))
        )

        today_by_disease = defaultdict(int)
        for row in today_qs:
            today_by_disease[get_disease_type(row['disease__name'])] += row['cnt']

        today_count = sum(today_by_disease.values())
        history_start = today - timedelta(days=8)
        spike_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(history_start, today),
                disease__isnull=False,
            )
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name')
            .annotate(case_count=Count('id'))
            .order_by('disease__name', 'appt_date')
        )

        daily_by_disease = defaultdict(lambda: defaultdict(int))
        for row in spike_qs:
            dtype = get_disease_type(row['disease__name'])
            daily_by_disease[dtype][row['appt_date']] += row['case_count']

        spike_alerts = []
        for dtype, daily_map in daily_by_disease.items():
            daily_list = [
                daily_map.get(history_start + timedelta(days=i), 0)
                for i in range(9)
            ]
            spike_info = detect_spike(daily_list, baseline_days=7)
            spike_alerts.append({
                'disease_name':      dtype,
                'today_count':       spike_info['today_count'],
                'mean_last_7_days':  spike_info['mean_last_7_days'],
                'threshold':         spike_info['threshold'],
                'std_dev':           spike_info['std_dev'],
                'is_spike':          spike_info['is_spike'],
            })

        spike_alerts = sorted(
            spike_alerts,
            key=lambda x: (not x['is_spike'], -x['today_count'])
        )[:8]

        critical_stock = DrugMaster.objects.filter(current_stock__lte=10).count()
        out_of_stock = DrugMaster.objects.filter(current_stock=0).count()
        low_stock_qs = (
            DrugMaster.objects
            .filter(current_stock__lte=50)
            .values('drug_name', 'generic_name')
            .annotate(total_stock=Sum('current_stock'))
            .order_by('total_stock')[:5]
        )
        low_stock_top = [
            {
                'drug_name':    row['drug_name'],
                'generic_name': row['generic_name'] or '',
                'current_stock': row['total_stock'] or 0,
            }
            for row in low_stock_qs
        ]

        recent_start = today - timedelta(days=6)
        older_start = today - timedelta(days=14)
        older_end = today - timedelta(days=7)

        recent_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(recent_start, today),
                disease__isnull=False,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(cnt=Count('id'))
        )
        older_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(older_start, older_end),
                disease__isnull=False,
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(cnt=Count('id'))
        )

        recent_map = defaultdict(int)
        older_map = defaultdict(int)
        for row in recent_qs:
            recent_map[get_disease_type(row['disease__name'])] += row['cnt']
        for row in older_qs:
            older_map[get_disease_type(row['disease__name'])] += row['cnt']

        trend_shifts = []
        for dtype in set(recent_map) | set(older_map):
            recent_value = recent_map.get(dtype, 0)
            older_value = older_map.get(dtype, 0)
            growth_rate = round(
                ((recent_value - older_value) / max(older_value, 1)) * 100,
                1
            )
            trend_shifts.append({
                'disease_name': dtype,
                'recent_count': recent_value,
                'prior_count': older_value,
                'growth_rate': growth_rate,
                'trend': 'up' if recent_value > older_value else 'down' if recent_value < older_value else 'stable',
            })

        trend_shifts = sorted(trend_shifts, key=lambda x: -x['growth_rate'])

        return Response({
            'date':              str(today),
            'total_appointments': today_count,
            'today_by_disease':  [
                {'disease_name': d, 'count': c}
                for d, c in sorted(today_by_disease.items(), key=lambda x: -x[1])
            ],
            'spike_alerts':      spike_alerts,
            'stock_risks': {
                'critical_count': critical_stock,
                'out_of_stock_count': out_of_stock,
                'top_low_stock': low_stock_top,
            },
            'trend_shifts': {
                'top_gainers': trend_shifts[:5],
                'top_decliners': list(reversed(trend_shifts[-5:])),
            },
        })




