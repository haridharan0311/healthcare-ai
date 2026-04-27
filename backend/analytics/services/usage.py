"""
Layer 2: Analytics - Usage Intelligence Module

Provides logic for analyzing consumption and behavior:
1. Medicine Usage Intelligence - Most used medicines per disease.
2. Doctor-wise Analytics - Patterns in disease handling per doctor.
3. Patient Demographic Usage - Insights across demographic groups.
"""

from datetime import timedelta
from typing import Dict, List, Optional, Union
from collections import defaultdict
from django.db.models import Count, Sum, Q
from django.utils import timezone

from analytics.models import Appointment
from inventory.models import PrescriptionLine, DrugMaster
from core.models import Doctor
from .aggregation import get_disease_type
from .timeseries import TimeSeriesAnalysis
from ..utils.date_utils import get_db_date_range
from ..utils.filters import apply_clinic_filter
from ..utils.logger import get_logger

# Configuration Constants
DEFAULT_USAGE_DAYS = 30
TOP_MEDS_PER_DISEASE_LIMIT = 15
TOP_DISEASES_STATS_LIMIT = 12
TOP_MEDS_PER_STATS_LIMIT = 5
DEFAULT_CRITICAL_STOCK_THRESHOLD = 10
DEFAULT_LOW_STOCK_THRESHOLD = 50

# Trend thresholds
GROWTH_RATE_RISING = 20
GROWTH_RATE_INCREASING = 5
GROWTH_RATE_DECREASING = -5

# Global filters for variants
VARIANT_FILTERS = Q(drug__drug_name__icontains='Vari') | Q(drug__drug_name__endswith=' V')

logger = get_logger(__name__)

class UsageIntelligence:
    """Service for behavior and consumption intelligence."""
    
    def __init__(self):
        self.logger = logger
        self.timeseries = None # Lazy load to avoid circular dependency

    def _get_timeseries_service(self):
        if self.timeseries is None:
            self.timeseries = TimeSeriesAnalysis()
        return self.timeseries

    def get_medicine_usage_per_disease(
        self, 
        disease_name: str, 
        days: int = DEFAULT_USAGE_DAYS, 
        rx_queryset=None
    ) -> Dict:
        """
        FEATURE 3: Medicine Usage Intelligence.
        Analyze which medicines are most used for a specific disease.
        """
        if rx_queryset is None:
            rx_queryset = PrescriptionLine.objects.all()
            
        try:
            start_date = timezone.now().date() - timedelta(days=days)
            
            filter_kwargs = {
                'prescription_date__gte': start_date,
                'disease__isnull': False
            }
            if disease_name and disease_name.lower() != 'all':
                filter_kwargs['disease__name__icontains'] = disease_name

            qs = (
                rx_queryset
                .filter(**filter_kwargs)
                .exclude(VARIANT_FILTERS)
                .select_related('drug')
                .values('drug__drug_name', 'drug__generic_name')
                .annotate(
                    total_quantity=Sum('quantity'),
                    prescription_count=Count('id')
                )
                .order_by('-total_quantity')
            )
            
            medicines = [
                {
                    'drug_name': row['drug__drug_name'],
                    'generic_name': row['drug__generic_name'],
                    'total_quantity': row['total_quantity'],
                    'prescription_count': row['prescription_count']
                }
                for row in qs[:TOP_MEDS_PER_DISEASE_LIMIT]
            ]
                
            return {
                'disease_name': disease_name,
                'period_days': days,
                'top_medicines': medicines
            }
        except Exception as e:
            self.logger.error(f"Medicine usage intelligence failed: {str(e)}", exc_info=True)
            return {'error': 'Failed to retrieve medicine usage data.'}

    def get_all_medicine_dependencies(self, days: int = DEFAULT_USAGE_DAYS, rx_queryset=None) -> List[Dict]:
        """
        Aggregates medicine usage for ALL diseases in a range.
        Returns format: [ { disease_name: 'X', total_prescriptions: N, unique_medicines: M, medicines: [...] }, ... ]
        """
        if rx_queryset is None:
            rx_queryset = PrescriptionLine.objects.all()
            
        start_date = timezone.now().date() - timedelta(days=days)
        
        # 1. Get all base prescription data
        base_qs = rx_queryset.filter(
            prescription_date__gte=start_date,
            disease__isnull=False
        ).exclude(VARIANT_FILTERS)
        
        # 2. Group by disease to get top-level stats
        disease_stats = base_qs.values('disease__name').annotate(
            total_rx=Count('id'),
            unique_meds=Count('drug', distinct=True)
        ).order_by('-total_rx')[:TOP_DISEASES_STATS_LIMIT]
        
        results = []
        for ds in disease_stats:
            d_name = ds['disease__name']
            # 3. For each top disease, get its top medicines
            meds_qs = base_qs.filter(disease__name=d_name).values(
                'drug__drug_name', 'drug__generic_name'
            ).annotate(
                cnt=Count('id')
            ).order_by('-cnt')[:TOP_MEDS_PER_STATS_LIMIT]
            
            meds_list = [
                {
                    'drug_name': m['drug__drug_name'],
                    'generic_name': m['drug__generic_name'],
                    'prescriptions': m['cnt']
                } 
                for m in meds_qs
            ]
            
            results.append({
                'disease_name': d_name,
                'total_prescriptions': ds['total_rx'],
                'unique_medicines': ds['unique_meds'],
                'medicines': meds_list
            })
            
        return results

    def get_doctor_patterns(
        self, 
        doctor_id: Optional[int] = None, 
        days: int = DEFAULT_USAGE_DAYS, 
        appt_queryset=None,
        request=None
    ) -> Union[Dict, List[Dict]]:
        """
        FEATURE 7: Doctor-wise Analytics.
        Tracks disease handling patterns and performance metrics per doctor.
        """
        try:
            start_date, end_date = get_db_date_range(days)
            
            if appt_queryset is None:
                appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)

            if doctor_id:
                qs = (
                    appt_queryset
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        doctor_id=doctor_id,
                        disease__isnull=False
                    )
                    .values('disease__name')
                    .annotate(cases=Count('id'))
                    .order_by('-cases')
                )
                
                doc = Doctor.objects.get(id=doctor_id)
                total_cases = sum(r['cases'] for r in qs)
                
                # Performance metrics
                days_active = max(days, 1)
                cases_per_day = round(total_cases / days_active, 2)
                
                # Fetch top drug prescribed by this doctor
                top_drug_qs = (
                    PrescriptionLine.objects
                    .filter(
                        prescription__doctor_id=doctor_id,
                        prescription_date__gte=start_date
                    )
                    .values('drug__drug_name')
                    .annotate(cnt=Count('id'))
                    .order_by('-cnt')[:1]
                )
                
                top_drug = top_drug_qs[0]['drug__drug_name'] if top_drug_qs else "N/A"

                return {
                    'doctor_name': f"{doc.first_name} {doc.last_name or ''}".strip(),
                    'total_cases': total_cases,
                    'cases_per_day': cases_per_day,
                    'top_prescribed_drug': top_drug,
                    'specialization_focus': get_disease_type(qs[0]['disease__name']) if qs else "None",
                    'disease_distribution': {get_disease_type(r['disease__name']): r['cases'] for r in qs}
                }
            else:
                # Summary view for all doctors
                qs = (
                    appt_queryset
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        disease__isnull=False
                    )
                    .values(
                        'doctor__id', 
                        'doctor__first_name', 
                        'doctor__last_name', 
                        'disease__name'
                    )
                    .annotate(cases=Count('id'))
                    .order_by('doctor__first_name', '-cases')
                )
                
                doctor_data = defaultdict(lambda: {'name': '', 'cases': 0, 'top_disease': '', 'max_d_cases': 0})
                for r in qs:
                    did = r['doctor__id']
                    dname = f"{r['doctor__first_name']} {r['doctor__last_name'] or ''}".strip()
                    dtype = get_disease_type(r['disease__name'])
                    
                    doctor_data[did]['name'] = dname
                    doctor_data[did]['cases'] += r['cases']
                    if r['cases'] > doctor_data[did]['max_d_cases']:
                        doctor_data[did]['max_d_cases'] = r['cases']
                        doctor_data[did]['top_disease'] = dtype
                
                results = [
                    {
                        'doctor_id': did,
                        'doctor_name': data['name'],
                        'total_cases': data['cases'],
                        'top_specialization': data['top_disease'],
                        'efficiency_score': round(data['cases'] / max(days, 1), 2)
                    } 
                    for did, data in doctor_data.items()
                ]
                
                # Sort by total_cases descending for "Top Doctors" ranking
                return sorted(results, key=lambda x: x['total_cases'], reverse=True)
        except Exception as e:
            self.logger.error(f"Doctor-wise analytics failed: {str(e)}", exc_info=True)
            return {'error': 'Failed to retrieve doctor analytics.'}

    def get_all_disease_trends(self, days: int = DEFAULT_USAGE_DAYS, appt_queryset=None, request=None) -> List[Dict]:
        """Get summary of all disease trends."""
        try:
            ts = self._get_timeseries_service()
            
            if appt_queryset is None:
                appt_queryset = apply_clinic_filter(Appointment.objects.all(), request)
            
            # Optimized bulk calculation
            growth_map = ts.calculate_bulk_growth_rates(days=days, appt_queryset=appt_queryset)
            
            results = []
            for dtype, rate in growth_map.items():
                if rate > GROWTH_RATE_RISING:
                    status = 'rising'
                elif rate > GROWTH_RATE_INCREASING:
                    status = 'increasing'
                elif rate < GROWTH_RATE_DECREASING:
                    status = 'decreasing'
                else:
                    status = 'stable'
                    
                results.append({
                    'disease_name': dtype,
                    'growth_rate': rate,
                    'status': status,
                    'direction': 'up' if rate > 0 else 'down' if rate < 0 else 'none'
                })
            return sorted(results, key=lambda x: x.get('growth_rate', 0), reverse=True)
        except Exception as e:
            self.logger.error(f"Failed to fetch disease trends: {str(e)}", exc_info=True)
            return []


    def get_stock_alerts(
        self, 
        critical_threshold: int = DEFAULT_CRITICAL_STOCK_THRESHOLD, 
        low_threshold: int = DEFAULT_LOW_STOCK_THRESHOLD, 
        request=None
    ) -> List[Dict]:
        """
        FEATURE 5: Low Stock Alerts.
        Identifies medicines in critical or low stock situations.
        """
        try:
            drugs_qs_base = DrugMaster.objects.filter(current_stock__lte=low_threshold).select_related('clinic')
            drugs = apply_clinic_filter(drugs_qs_base, request)
            
            results = []
            for drug in drugs:
                status = 'critical' if drug.current_stock <= critical_threshold else 'low'
                results.append({
                    'drug_id': drug.id,
                    'drug_name': drug.drug_name,
                    'current_stock': drug.current_stock,
                    'status': status,
                    'clinic': drug.clinic.clinic_name if drug.clinic else "Unknown"
                })
            return sorted(results, key=lambda x: (x['status'] == 'low', x['current_stock']))
        except Exception as e:
            self.logger.error(f"Stock alerts failed: {str(e)}", exc_info=True)
            return []

