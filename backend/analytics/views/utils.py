import re
from datetime import date, timedelta
from django.core.cache import cache
from rest_framework.response import Response
from django.db.models import Max
from analytics.models import Appointment
from ..services.aggregation import build_daily_list

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
            cache_key = f"{self.__class__.__name__}:{request.GET.urlencode()}"
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
            response = view_func(self, request, *args, **kwargs)
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            return response
        return wrapper
    return decorator


GENERIC_MAP = {
    'Paracetamol':       'Acetaminophen',
    'Ibuprofen':         'Ibuprofen',
    'Amoxicillin':       'Amoxicillin trihydrate',
    'Metformin':         'Metformin hydrochloride',
    'Aspirin':           'Acetylsalicylic acid',
    'Cetirizine':        'Cetirizine hydrochloride',
    'Azithromycin':      'Azithromycin dihydrate',
    'Ciprofloxacin':     'Ciprofloxacin hydrochloride',
    'Doxycycline':       'Doxycycline hyclate',
    'Diclofenac':        'Diclofenac sodium',
    'Chlorpheniramine':  'Chlorpheniramine maleate',
    'Montelukast':       'Montelukast sodium',
    'Glibenclamide':     'Glibenclamide',
    'Glimepiride':       'Glimepiride',
    'Insulin (Regular)': 'Human insulin',
    'Amlodipine':        'Amlodipine besylate',
    'Atenolol':          'Atenolol',
    'Losartan':          'Losartan potassium',
    'Enalapril':         'Enalapril maleate',
    'Salbutamol':        'Albuterol sulfate',
    'Prednisolone':      'Prednisolone',
    'Theophylline':      'Theophylline anhydrous',
    'Omeprazole':        'Omeprazole magnesium',
    'Ranitidine':        'Ranitidine hydrochloride',
    'Domperidone':       'Domperidone',
    'Vitamin C':         'Ascorbic acid',
    'Vitamin D3':        'Cholecalciferol',
    'Zinc Sulphate':     'Zinc sulfate monohydrate',
    'ORS':               'Oral Rehydration Salts',
    'Chloroquine':       'Chloroquine phosphate',
}

def _get_generic(drug_name: str) -> str:
    return GENERIC_MAP.get(drug_name, drug_name)

def _extract_district(address: str) -> str:
    if not address:
        return 'Unknown'
    parts = [p.strip() for p in address.split(',')]
    return parts[4].strip() if len(parts) >= 5 else 'Unknown'

def _get_db_date_range(days: int = 30):
    cache_key = 'latest_appointment_date'
    latest_dt = cache.get(cache_key)
    
    if latest_dt is None:
        latest_dt = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']
        if latest_dt:
            cache.set(cache_key, latest_dt, 1800)  # Cache for 30 minutes
            
    end   = latest_dt.date() if latest_dt else date.today()
    start = end - timedelta(days=days)
    return start, end

def _get_date_range(request):
    try:
        days = int(request.query_params.get('days', 30))
    except ValueError:
        days = 30
    return _get_db_date_range(days)

