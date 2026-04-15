import datetime
from datetime import date, timedelta, datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from analytics.models import Appointment
from .utils import apply_clinic_filter

class DashboardStatsView(APIView):
    """Returns top-level analytics metrics (Sub-second)."""
    def get(self, request):
        # Use consistent latest date from database
        from .utils import _get_db_date_range
        _, end_date = _get_db_date_range(0)
        
        # 1. Today (Latest system date)
        today_start = datetime.combine(end_date, time.min)
        today_end   = datetime.combine(end_date, time.max)
        
        total_today = apply_clinic_filter(
            Appointment.objects.filter(appointment_datetime__range=(today_start, today_end), disease__isnull=False),
            request
        ).count()

        # 2. Week-to-Date (from Monday)
        wtd_start_date = end_date - timedelta(days=end_date.weekday())
        wtd_start = datetime.combine(wtd_start_date, time.min)
        total_wtd = apply_clinic_filter(
            Appointment.objects.filter(appointment_datetime__range=(wtd_start, today_end), disease__isnull=False),
            request
        ).count()

        # 3. Month-to-Date (from 1st)
        mtd_start_date = end_date.replace(day=1)
        mtd_start = datetime.combine(mtd_start_date, time.min)
        total_mtd = apply_clinic_filter(
            Appointment.objects.filter(appointment_datetime__range=(mtd_start, today_end), disease__isnull=False),
            request
        ).count()

        return Response({
            'total_today': total_today,
            'total_wtd':   total_wtd,
            'total_mtd':   total_mtd,
            'total_last_30_days': total_mtd, # Legacy fallback
            'active_outbreaks': 0,
            'risk_status': 'Stable'
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
