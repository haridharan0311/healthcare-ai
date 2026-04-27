from datetime import date
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from analytics.models import Appointment
from inventory.models import PrescriptionLine, DrugMaster
from ..services.usage import UsageIntelligence
from ..services.forecasting import ForecastingService
from ..services.aggregation import aggregate_medicine_usage, aggregate_top_medicines_with_stock
from ..utils.validators import validate_positive_int
from .utils import cache_api_response, _get_date_range, apply_clinic_filter

# medicine_views.py extracted classes

class MedicineUsageView(APIView):
    """
    GET /api/medicine-usage/?days=30
    
    1.3 Medicine Usage Aggregation.
    Calculates total medicine usage per disease using optimized DB-driven aggregation.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        start, end = _get_date_range(request)
        
        # Prepare filtered querysets for the aggregation layer
        rx_qs = apply_clinic_filter(PrescriptionLine.objects.all(), request, clinic_field='prescription__clinic')
        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        
        # Use centralized aggregation logic to ensure consistency across the platform
        results = aggregate_medicine_usage(
            start=start, 
            end=end, 
            rx_queryset=rx_qs, 
            appt_queryset=appt_qs
        )
        
        # Inject period info for frontend context
        for r in results:
            r['period_start'] = str(start)
            r['period_end'] = str(end)
            
        return Response(results)


# ─── 2.3 Spike Detection → Spike Alert API ───────────────────────────────────



class TopMedicinesView(APIView):
    """
    GET /api/top-medicines/?days=30&limit=10
    
    Shows top medicines by usage along with their current live stock levels.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        start, end = _get_date_range(request)
        limit = validate_positive_int(
            request.query_params.get('limit'), 
            'limit', 
            default=10, 
            min_value=1, 
            max_value=50
        )

        # Prepare filtered querysets
        rx_qs = apply_clinic_filter(PrescriptionLine.objects.all(), request, clinic_field='prescription__clinic')
        stock_qs = apply_clinic_filter(DrugMaster.objects.all(), request)
        
        # Exclude specific variants if needed (logic encapsulated in aggregation or applied here)
        rx_qs = rx_qs.exclude(Q(drug__drug_name__icontains='Vari') | Q(drug__drug_name__endswith=' V'))

        results = aggregate_top_medicines_with_stock(
            start=start,
            end=end,
            limit=limit,
            rx_queryset=rx_qs,
            stock_queryset=stock_qs
        )

        return Response({
            'period': f'{start} to {end}',
            'total_drugs_in_period': len(results), # This is a simplified count for the top N
            'top_medicines': results,
        })

# ── New Feature 3: Low Stock Alert System ────────────────────────────────────



class LowStockAlertView(APIView):
    """
    GET /api/low-stock-alerts/?threshold=50
    
    Unified Low Stock Alert System.
    Identifies medicines across clinics that are below a safe threshold.
    """
    @cache_api_response(timeout=300)
    def get(self, request):
        threshold = validate_positive_int(
            request.query_params.get('threshold'), 
            'threshold', 
            default=50
        )
        
        usage_service = UsageIntelligence()
        # Leveraging the service layer for business logic
        alerts = usage_service.get_stock_alerts(
            low_threshold=threshold, 
            request=request
        )
        
        # Categorize alerts for the dashboard counters
        summary = {
            'threshold': threshold,
            'total_alerts': len(alerts),
            'critical': sum(1 for a in alerts if a['status'] == 'critical'),
            'low': sum(1 for a in alerts if a['status'] == 'low'),
            'alerts': alerts
        }
        
        return Response(summary)

# ─── Seasonality ───────────────────────────



class MedicineDependencyView(APIView):
    """
    GET /api/medicine-dependency/?days=30&disease=Flu

    Returns which medicines are most commonly used for each disease.
    """
    @cache_api_response(timeout=300)  # Cache for 30s
    def get(self, request):
        days = validate_positive_int(request.query_params.get('days'), 'days', default=30, min_value=1, max_value=365)
        disease_name = request.query_params.get('disease')

        service = UsageIntelligence()
        rx_qs_base = PrescriptionLine.objects.all()
        rx_qs = apply_clinic_filter(rx_qs_base, request, clinic_field='prescription__clinic')

        if not disease_name or disease_name.lower() == 'all':
            # Aggregated view for all diseases
            result = service.get_all_medicine_dependencies(days=days, rx_queryset=rx_qs)
        else:
            # Single disease focus
            result = service.get_medicine_usage_per_disease(
                disease_name=disease_name,
                days=days,
                rx_queryset=rx_qs
            )
        return Response(result)




class StockDepletionForecastView(APIView):
    """
    GET /api/stock-depletion/?drug_id=5&days=30

    Provides stock depletion forecast for a specific medicine.
    """
    def get(self, request):
        drug_id = request.query_params.get('drug_id')
        drug_name = request.query_params.get('drug_name')
        
        # Use a more generous window for depletion analysis if requested
        days = validate_positive_int(request.query_params.get('days'), 'days', default=30, min_value=1, max_value=365)
        
        if not drug_id and not drug_name:
            return Response(
                {'error': 'Provide drug_id or drug_name'},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        # If we have a drug_id, we get its specific name for the aggregated service
        target_name = drug_name
        if not target_name and drug_id:
            try:
                target_name = DrugMaster.objects.get(id=drug_id).drug_name
            except DrugMaster.DoesNotExist:
                return Response({'error': 'Drug ID not found'}, status=drf_status.HTTP_404_NOT_FOUND)

        rx_qs_base = PrescriptionLine.objects.all()
        rx_qs = apply_clinic_filter(rx_qs_base, request, clinic_field='prescription__clinic')
        
        from ..services.forecasting import ForecastingService
        service = ForecastingService()
        result = service.forecast_stock_depletion(drug_name=target_name, days=days, rx_queryset=rx_qs, request=request)

        if result.get('error'):
            return Response(result, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(result)

