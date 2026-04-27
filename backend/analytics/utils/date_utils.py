from datetime import date, timedelta
from django.db.models import Max
from django.core.cache import cache
from analytics.models import Appointment

def get_latest_activity_date():
    """
    Returns the date of the most recent appointment in the system.
    Used as the 'Today' anchor for all analytics.
    """
    cache_key = 'latest_appointment_date'
    latest_dt = cache.get(cache_key)
    
    if latest_dt is None:
        latest_dt = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        if latest_dt:
            cache.set(cache_key, latest_dt, 60)  # Cache for 1 minute
            
    return latest_dt.date() if latest_dt else date.today()

def get_db_date_range(days: int = 30):
    """
    Returns (start, end) dates relative to the latest system activity.
    """
    end = get_latest_activity_date()
    start = end - timedelta(days=days)
    return start, end
