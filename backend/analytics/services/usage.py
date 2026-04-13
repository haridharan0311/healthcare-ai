"""
Layer 2: Analytics - Usage Intelligence Module

Provides logic for analyzing consumption and behavior:
1. Medicine Usage Intelligence - Most used medicines per disease.
2. Doctor-wise Analytics - Patterns in disease handling per doctor.
3. Patient Demographic Usage - Insights across demographic groups.

Usage:
    from analytics.services.usage import UsageIntelligence
    
    ui = UsageIntelligence()
    med_intel = ui.get_medicine_usage_per_disease("Flu")
    doc_intel = ui.get_doctor_patterns(doctor_id=1)
"""

from datetime import date, timedelta
from typing import Dict, List, Optional
from django.db.models import Count, Sum
from inventory.models import PrescriptionLine, DrugMaster
from core.models import Doctor
from .aggregation import get_disease_type
from ..utils.logger import get_logger

logger = get_logger(__name__)

class UsageIntelligence:
    """Service for behavior and consumption intelligence."""
    
    def __init__(self):
        self.logger = logger

    def get_medicine_usage_per_disease(self, disease_name: str, days: int = 30) -> Dict:
        """
        FEATURE 3: Medicine Usage Intelligence.
        Analyze which medicines are most used for a specific disease.
        """
        try:
            start_date = date.today() - timedelta(days=days)
            qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__gte=start_date,
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .select_related('drug')
                .values('drug__drug_name', 'drug__generic_name')
                .annotate(
                    total_quantity=Sum('quantity'),
                    prescription_count=Count('id')
                )
                .order_by('-total_quantity')
            )
            
            medicines = []
            for row in qs:
                medicines.append({
                    'drug_name': row['drug__drug_name'],
                    'generic_name': row['drug__generic_name'],
                    'total_quantity': row['total_quantity'],
                    'prescription_count': row['prescription_count']
                })
                
            return {
                'disease_name': disease_name,
                'period_days': days,
                'top_medicines': medicines[:10]
            }
        except Exception as e:
            self.logger.error(f"Medicine usage intelligence failed: {str(e)}")
            return {'error': str(e)}

    def get_doctor_patterns(self, doctor_id: Optional[int] = None, days: int = 30) -> Dict or List[Dict]:
        """
        FEATURE 7: Doctor-wise Analytics.
        Tracks disease handling patterns per doctor.
        """
        try:
            start_date = date.today() - timedelta(days=days)
            from analytics.models import Appointment
            
            if doctor_id:
                qs = Appointment.objects.filter(
                    appointment_datetime__date__gte=start_date, 
                    doctor_id=doctor_id,
                    disease__isnull=False
                ).select_related('doctor', 'disease').values('disease__name').annotate(cases=Count('id')).order_by('-cases')
                
                doc = Doctor.objects.get(id=doctor_id)
                return {
                    'doctor_name': f"{doc.first_name} {doc.last_name or ''}".strip(),
                    'total_cases': sum(r['cases'] for r in qs),
                    'specialization_focus': get_disease_type(qs[0]['disease__name']) if qs else "None",
                    'disease_distribution': {get_disease_type(r['disease__name']): r['cases'] for r in qs}
                }
            else:
                qs = Appointment.objects.filter(
                    appointment_datetime__date__gte=start_date,
                    disease__isnull=False
                ).select_related('doctor', 'disease').values('doctor__first_name', 'doctor__last_name', 'disease__name').annotate(cases=Count('id')).order_by('doctor__first_name', '-cases')
                
                return [{
                    'doctor_name': f"{r['doctor__first_name']} {r['doctor__last_name'] or ''}".strip(),
                    'disease': get_disease_type(r['disease__name']),
                    'cases': r['cases']
                } for r in qs]
        except Exception as e:
            self.logger.error(f"Doctor-wise analytics failed: {str(e)}")
            return {'error': str(e)}

    def get_all_disease_trends(self, days: int = 30) -> List[Dict]:
        """Get summary of all disease trends."""
        from .timeseries import TimeSeriesAnalysis
        ts = TimeSeriesAnalysis()
        from analytics.models import Disease
        
        diseases = Disease.objects.filter(is_active=True).values_list('name', flat=True).distinct()
        results = []
        for dname in diseases:
            dtype = get_disease_type(dname)
            growth = ts.calculate_growth_rate(dtype, days=days)
            results.append(growth)
        return sorted(results, key=lambda x: x.get('growth_rate', 0), reverse=True)

    def get_stock_alerts(self, critical_threshold: int = 10, low_threshold: int = 50) -> List[Dict]:
        """
        FEATURE 5: Low Stock Alerts.
        Identifies medicines in critical or low stock situations.
        """
        try:
            from inventory.models import DrugMaster
            drugs = DrugMaster.objects.filter(current_stock__lte=low_threshold)
            
            results = []
            for drug in drugs:
                status = 'critical' if drug.current_stock <= critical_threshold else 'low'
                results.append({
                    'drug_id': drug.id,
                    'drug_name': drug.drug_name,
                    'current_stock': drug.current_stock,
                    'status': status,
                    'clinic': drug.clinic.clinic_name
                })
            return sorted(results, key=lambda x: (x['status'] == 'low', x['current_stock']))
        except Exception as e:
            self.logger.error(f"Stock alerts failed: {str(e)}")
            return []
