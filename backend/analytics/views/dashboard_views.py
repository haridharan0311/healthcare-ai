import datetime
from datetime import date, timedelta, time
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from analytics.models import Appointment
from .utils import apply_clinic_filter, _get_db_date_range
from ..services.aggregation import aggregate_disease_counts, aggregate_daily_counts, build_daily_list
from ..services.spike_detection import detect_spike_logic

class DashboardStatsView(APIView):
    """Returns top-level analytics metrics (Sub-second)."""
    def get(self, request):
        # Use consistent latest date from database
        _, end_date = _get_db_date_range(0)
        
        # 1. Today (Latest system date)
        today_start = timezone.make_aware(datetime.datetime.combine(end_date, time.min))
        today_end   = timezone.make_aware(datetime.datetime.combine(end_date, time.max))
        
        base_qs = Appointment.objects.filter(disease__isnull=False)
        filtered_qs = apply_clinic_filter(base_qs, request)

        total_today = filtered_qs.filter(appointment_datetime__range=(today_start, today_end)).count()

        # 2. Week-to-Date (from Monday)
        wtd_start_date = end_date - timedelta(days=end_date.weekday())
        wtd_start = timezone.make_aware(datetime.datetime.combine(wtd_start_date, time.min))
        total_wtd = filtered_qs.filter(appointment_datetime__range=(wtd_start, today_end)).count()

        # 3. Month-to-Date (from 1st)
        mtd_start_date = end_date.replace(day=1)
        mtd_start = timezone.make_aware(datetime.datetime.combine(mtd_start_date, time.min))
        total_mtd = filtered_qs.filter(appointment_datetime__range=(mtd_start, today_end)).count()

        # 4. Top Disease (Today)
        top_disease = "None"
        today_counts = aggregate_disease_counts(end_date, end_date, queryset=filtered_qs)
        if today_counts:
            top_disease = max(today_counts.items(), key=lambda x: x[1]['count'])[0]

        # 5. Active Outbreaks (Last 7 days)
        active_outbreaks = 0
        spike_start = end_date - timedelta(days=7)
        daily_map = aggregate_daily_counts(spike_start, end_date, queryset=filtered_qs)
        for dtype, data in daily_map.items():
            counts_list = build_daily_list(data.get('daily', {}), spike_start, end_date)
            if detect_spike_logic(counts_list).get('is_spike'):
                active_outbreaks += 1

        return Response({
            'total_today': total_today,
            'total_wtd':   total_wtd,
            'total_mtd':   total_mtd,
            'top_disease': top_disease,
            'active_outbreaks': active_outbreaks,
            'risk_status': 'Stable' if active_outbreaks == 0 else ('Elevated' if active_outbreaks < 3 else 'Critical')
        })

class DashboardTrendsView(APIView):
    """Returns disease trends and forecasts (Sub-second)."""
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        fc_days = int(request.query_params.get('forecast_days', 8))
        # Pass request to apply clinic filter
        from ..services.dashboard_service import DashboardService
        data = DashboardService.get_trends_fragment(days=days, forecast_days=fc_days, request=request)
        return Response(data)

class DashboardMedicinesView(APIView):
    """Returns medicine restock suggestions (Isolated Heavy 2.8M row scan)."""
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        # Pass request to apply clinic filter
        from ..services.dashboard_service import DashboardService
        data = DashboardService.get_medicines_fragment(days=days, request=request)
        return Response(data)
