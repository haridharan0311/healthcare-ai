from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from core.models import Clinic
from analytics.models import Appointment
from .utils import cache_api_response

class StateAnalyticsView(APIView):
    """
    GET /api/districts/state-summary/
    
    Aggregates data across all clinics to provide a 'State-Level' overview.
    Used for the Heat Map visualization in the dashboard.
    """
    @cache_api_response(timeout=3600) # Long cache for state data
    def get(self, request):
        # 1. Aggregate cases by clinic location
        # Assume clinic_address_1 or a new 'district' field represents the location
        # For now, we group by clinic and return their coordinates/counts
        
        state_data = (
            Appointment.objects.values('clinic__clinic_name', 'clinic__clinic_address_1')
            .annotate(case_count=Count('id'))
            .order_by('-case_count')
        )
        
        # 2. Transform into a map-friendly format
        # In a real app, you'd store Lat/Long in the Clinic model.
        # Here we simulate some geographic grouping.
        results = []
        for entry in state_data:
            results.append({
                'district': entry['clinic__clinic_address_1'],
                'clinic': entry['clinic__clinic_name'],
                'value': entry['case_count'],
                # Simulated coordinates for a heat map
                'lat': 13.0827, # Chennai default as example
                'lng': 80.2707,
            })

        return Response({
            'success': True,
            'state': 'Tamil Nadu', # Example
            'total_districts': len(results),
            'map_data': results,
            'summary': {
                'peak_district': results[0]['district'] if results else 'N/A',
                'peak_count': results[0]['value'] if results else 0
            }
        })
