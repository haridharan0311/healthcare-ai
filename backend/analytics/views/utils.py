import re
from datetime import date, timedelta
from django.core.cache import cache
from rest_framework.response import Response
from django.db.models import Max
from analytics.models import Appointment
from ..services.aggregation import build_daily_list
from ..utils.chemistry import GENERIC_MAP, _get_generic
from ..utils.geo import _extract_district

def _build_daily_list(daily_map_by_type, disease_type, start_date, end_date):
    """
    Adapter for legacy views using the 4-arg signature.
    Fills zeros for missing days in a range.
    """
    daily_counts = daily_map_by_type.get(disease_type, {})
    return build_daily_list(daily_counts, start_date, end_date)


def cache_api_response(timeout=300):
    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            cache_key = f"{self.__class__.__name__}:{user_id}:{request.GET.urlencode()}"
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
            response = view_func(self, request, *args, **kwargs)
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            return response
        return wrapper
    return decorator


def _get_db_date_range(days: int = 30):
    cache_key = 'latest_appointment_date'
    latest_dt = cache.get(cache_key)
    
    if latest_dt is None:
        latest_dt = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        if latest_dt:
            cache.set(cache_key, latest_dt, 60)  # Cache for 1 minute
            
    end   = latest_dt.date() if latest_dt else date.today()
    start = end - timedelta(days=days)
    return start, end

def _get_date_range(request):
    """
    Returns (start, end) dates.
    Supports ?days=N or ?period=MTD|WTD.
    """
    try:
        days = int(request.query_params.get('days', 30))
    except ValueError:
        days = 30
    
    start, end = _get_db_date_range(days)
    
    period = request.query_params.get('period', '').upper()
    if period == 'MTD':
        # Month-to-Date: from 1st of current (latest) month
        start = end.replace(day=1)
    elif period == 'WTD':
        # Week-to-Date: from start of current week (assume Monday)
        start = end - timedelta(days=end.weekday())
        
    return start, end

from ..utils.filters import apply_clinic_filter

# Re-exporting for compatibility with existing views
__all__ = [
    'apply_clinic_filter',
    '_get_date_range',
    '_get_db_date_range',
    '_build_daily_list',
    'cache_api_response',
    '_get_generic',
    'GENERIC_MAP',
    '_extract_district'
]
