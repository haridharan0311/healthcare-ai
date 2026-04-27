from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from analytics.models import Appointment
from ..services.spike_detection import detect_spike_logic as detect_spike
from ..serializers.serializers import SpikeAlertSerializer
from ..utils.date_utils import get_db_date_range
from .utils import cache_api_response, apply_clinic_filter, _build_daily_list
from ..services.aggregation import get_disease_type, aggregate_daily_counts

# Configuration Constants
DASHBOARD_CACHE_TIMEOUT = 300
DEFAULT_BASELINE_DAYS = 8

class SpikeAlertView(APIView):
    """
    GET /api/spike-alerts/?days=8&all=true
    
    2.3 Spike Detection: today_count > (mean_last_N_days + 2 × std_dev)
    Identifies statistical anomalies in disease distribution.
    """
    @cache_api_response(timeout=DASHBOARD_CACHE_TIMEOUT)
    def get(self, request):
        show_all = request.query_params.get('all', 'false').lower() == 'true'
        days = DEFAULT_BASELINE_DAYS
        
        # Consistent system-wide date anchoring
        start, end = get_db_date_range(days)

        # Optimize data retrieval via service-style aggregation
        appt_qs = apply_clinic_filter(Appointment.objects.all(), request)
        daily_map = aggregate_daily_counts(start, end, queryset=appt_qs)

        if not daily_map:
            return Response([])

        baseline_days = days - 1
        results = []

        for dtype, disease_data in daily_map.items():
            # Standardize daily counts into a list for the statistical engine
            daily_counts = _build_daily_list(daily_map, dtype, start, end)
            
            # Apply detection logic
            spike_info = detect_spike(daily_counts, baseline_days=baseline_days)
            period_count = sum(daily_counts)

            if spike_info['is_spike'] or show_all:
                results.append({
                    'disease_name': dtype,
                    'period_count': period_count,
                    **spike_info
                })

        # Sort by impact (today's count)
        results.sort(key=lambda x: x['today_count'], reverse=True)
        serializer = SpikeAlertSerializer(results, many=True)
        return Response(serializer.data)


# ─── 2.4 + 2.5 Demand & Restock → Restock Suggestions API ───────────────────



