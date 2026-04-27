from datetime import datetime, date, timedelta, time
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from analytics.models import Appointment
from .utils import apply_clinic_filter, _get_db_date_range
from ..services.aggregation import aggregate_disease_counts, aggregate_daily_counts, build_daily_list
from ..services.spike_detection import detect_spike_logic
from ..services.dashboard_service import DashboardService
from ..utils.logger import get_logger

# Configuration Constants
DEFAULT_TREND_DAYS = 30
DEFAULT_FORECAST_DAYS = 8
OUTBREAK_RISK_ELEVATED_THRESHOLD = 3
OUTBREAK_SPIKE_LOOKBACK_DAYS = 7

logger = get_logger(__name__)

class DashboardStatsView(APIView):
    """Returns top-level analytics metrics for the main dashboard."""
    
    def get(self, request):
        try:
            # Use consistent latest date from database to ensure multi-tenancy consistency
            _, end_date = _get_db_date_range(0)
            
            # 1. Today (Latest system date boundaries)
            today_start = timezone.make_aware(datetime.combine(end_date, time.min))
            today_end   = timezone.make_aware(datetime.combine(end_date, time.max))
            
            base_qs = Appointment.objects.filter(disease__isnull=False)
            filtered_qs = apply_clinic_filter(base_qs, request)

            # Performance: Keep isolated for readability and DB-level count optimization
            total_today = filtered_qs.filter(appointment_datetime__range=(today_start, today_end)).count()

            # 2. Week-to-Date (from start of current week)
            wtd_start_date = end_date - timedelta(days=end_date.weekday())
            wtd_start = timezone.make_aware(datetime.combine(wtd_start_date, time.min))
            total_wtd = filtered_qs.filter(appointment_datetime__range=(wtd_start, today_end)).count()

            # 3. Month-to-Date (from 1st of current month)
            mtd_start_date = end_date.replace(day=1)
            mtd_start = timezone.make_aware(datetime.combine(mtd_start_date, time.min))
            total_mtd = filtered_qs.filter(appointment_datetime__range=(mtd_start, today_end)).count()

            # 4. Top Disease (Today)
            top_disease = "None"
            today_counts = aggregate_disease_counts(end_date, end_date, queryset=filtered_qs)
            if today_counts:
                top_disease = max(today_counts.items(), key=lambda x: x[1]['count'])[0]

            # 5. Active Outbreaks (Last N days)
            active_outbreaks = 0
            spike_start = end_date - timedelta(days=OUTBREAK_SPIKE_LOOKBACK_DAYS)
            daily_map = aggregate_daily_counts(spike_start, end_date, queryset=filtered_qs)
            
            for disease_data in daily_map.values():
                counts_list = build_daily_list(disease_data.get('daily', {}), spike_start, end_date)
                if detect_spike_logic(counts_list).get('is_spike'):
                    active_outbreaks += 1

            # Determine Risk Status based on active outbreaks
            if active_outbreaks == 0:
                risk_status = 'Stable'
            elif active_outbreaks < OUTBREAK_RISK_ELEVATED_THRESHOLD:
                risk_status = 'Elevated'
            else:
                risk_status = 'Critical'

            return Response({
                'total_today': total_today,
                'total_wtd':   total_wtd,
                'total_mtd':   total_mtd,
                'top_disease': top_disease,
                'active_outbreaks': active_outbreaks,
                'risk_status': risk_status
            })
        except Exception as e:
            logger.error(f"Dashboard stats failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to retrieve dashboard statistics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardTrendsView(APIView):
    """Returns disease trends and predictive forecasts."""
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', DEFAULT_TREND_DAYS))
            fc_days = int(request.query_params.get('forecast_days', DEFAULT_FORECAST_DAYS))
            
            data = DashboardService.get_trends_fragment(days=days, forecast_days=fc_days, request=request)
            return Response(data)
        except Exception as e:
            logger.error(f"Dashboard trends failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to retrieve trend data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardMedicinesView(APIView):
    """Returns medicine restock suggestions and consumption patterns."""
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', DEFAULT_TREND_DAYS))
            data = DashboardService.get_medicines_fragment(days=days, request=request)
            return Response(data)
        except Exception as e:
            logger.error(f"Dashboard medicines failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to retrieve medicine metrics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
