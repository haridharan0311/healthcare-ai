from rest_framework.views import APIView
from rest_framework.response import Response
from ..services.dashboard_service import DashboardService

class DashboardStatsView(APIView):
    """Returns top-level analytics metrics (Sub-second)."""
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        # Call specialized LIGHTWEIGHT fragment
        data = DashboardService.get_stats_fragment(days=days)
        return Response(data)

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
