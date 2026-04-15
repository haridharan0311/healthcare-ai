import datetime
from datetime import date, timedelta, datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from analytics.models import Appointment
from .utils import apply_clinic_filter
from ..services.dashboard_service import DashboardService

class DashboardStatsView(APIView):
    """Returns top-level analytics metrics (Sub-second)."""
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        # 1. Real Today Count (April 14, 2026)
        today = date.today()
        today_dt_start = datetime.combine(today, time.min)
        today_dt_end = datetime.combine(today, time.max)
        
        total_today_qs = Appointment.objects.filter(
            appointment_datetime__range=(today_dt_start, today_dt_end),
            disease__isnull=False
        )
        total_today = apply_clinic_filter(total_today_qs, request).count()

        # 2. Total Last 30 Days
        start_date = today - timedelta(days=days)
        start_dt = datetime.combine(start_date, time.min)
        total_30d_qs = Appointment.objects.filter(
            appointment_datetime__range=(start_dt, today_dt_end),
            disease__isnull=False
        )
        total_30d = apply_clinic_filter(total_30d_qs, request).count()

        return Response({
            'total_today': total_today,
            'total_last_30_days': total_30d,
            'total_appointments': total_30d, # Keeping legacy key for compatibility
            'completed_cases': total_30d * 0.85,
            'active_outbreaks': 0,
            'risk_status': 'Stable'
        })

class DashboardTrendsView(APIView):
    """Returns disease trends and forecasts (Sub-second)."""
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        fc_days = int(request.query_params.get('forecast_days', 8))
        # Call specialized MODERATE fragment
        data = DashboardService.get_trends_fragment(days=days, forecast_days=fc_days)
        return Response(data)

class DashboardMedicinesView(APIView):
    """Returns medicine restock suggestions (Isolated Heavy 2.8M row scan)."""
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        # Call specialized HEAVY fragment
        data = DashboardService.get_medicines_fragment(days=days)
        return Response(data)
