from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class DiseaseTrendView(APIView):
    def get(self, request):
        # Phase 3: query Appointment, apply seasonal scoring
        return Response({"message": "disease-trends — coming in Phase 3"})


class TimeSeriesView(APIView):
    def get(self, request):
        # Phase 3: daily aggregation, 7/30 day filter
        return Response({"message": "timeseries — coming in Phase 3"})


class SpikeAlertView(APIView):
    def get(self, request):
        # Phase 3: call spike_detector.py
        return Response({"message": "spike-alerts — coming in Phase 3"})


class RestockSuggestionView(APIView):
    def get(self, request):
        # Phase 3: call ml_engine + restock_calculator
        return Response({"message": "restock-suggestions — coming in Phase 3"})


class ExportReportView(APIView):
    def get(self, request):
        # Phase 3: return CSV response
        return Response({"message": "export-report — coming in Phase 3"})
