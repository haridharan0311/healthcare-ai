"""
Restock Service Module

Intelligent medicine restock recommendations with adaptive buffers:
1. Adaptive Safety Buffer - dynamically adjusts based on spike patterns
2. Multi-disease contribution - combines demand from multiple diseases
3. District-level recommendations - aggregates across clinics
4. Critical stock alerts - prioritizes urgent needs

Layer: Services (Business Logic)
Dependencies: restock_calculator, spike_detection, forecasting, logger

Usage:
    from analytics.services.restock_service import RestockService
    
    service = RestockService()
    
    # Get restock suggestions
    suggestions = service.calculate_restock_suggestions()
    
    # Get district-specific recommendations
    district = service.get_district_restock("Tamil Nadu")
    
    # Adaptive buffer based on current spikes
    buffer = service.calculate_adaptive_buffer()
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional

from django.db.models import Count, Sum, Max, Q
from django.db.models.functions import TruncDate

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic
from ..services.aggregation import get_disease_type
from .ml_engine import (
    moving_average_forecast,
    weighted_trend_score,
    predict_demand
)
from .restock_calculator import (
    calculate_restock,
    calculate_dynamic_safety_buffer,
    apply_multi_disease_contribution,
    BASE_SAFETY_BUFFER,
    MAX_SAFETY_BUFFER
)
from .timeseries import get_seasonal_weight
from .spike_detection import detect_spike_logic as detect_spike
from ..views.utils import apply_clinic_filter
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class RestockService:
    """
    Service for restock recommendations and inventory planning.
    
    For new users: Uses disease forecasts, consumption patterns, and spike
    detection to recommend optimal restock quantities.
    """
    
    def __init__(self):
        """Initialize service."""
        self.logger = logger
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 5: Adaptive Safety Buffer
    # Dynamically adjusts restock buffer based on spike patterns
    # ────────────────────────────────────────────────────────────────────────────
    
    def calculate_adaptive_buffer(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        daily_by_disease: Optional[Dict] = None,
        request = None
    ) -> Dict:
        """
        FEATURE 5: Calculate adaptive safety buffer based on current spike situation.
        Optimized: Accepts pre-calculated daily counts to avoid redundant DB scans.
        """
        try:
            if daily_by_disease is None:
                if start_date is None or end_date is None:
                    start_date, end_date = validate_date_range()
                
                # Optimized query: avoids select_related, uses values() directly
                qs_base = Appointment.objects.filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__isnull=False
                )
                qs = apply_clinic_filter(qs_base, request) \
                    .annotate(appt_date=TruncDate('appointment_datetime')) \
                    .values('appt_date', 'disease__name') \
                    .annotate(day_count=Count('id'))
                
                daily_by_disease = defaultdict(lambda: defaultdict(int))
                for row in qs:
                    disease = get_disease_type(row['disease__name'])
                    daily_by_disease[disease][row['appt_date']] += row['day_count']
            
            spike_count = 0
            for disease, daily_map in daily_by_disease.items():
                # Avoid sorting if possible, or use a fixed window
                daily_counts = [daily_map.get(start_date + timedelta(days=i), 0) 
                               for i in range((end_date - start_date).days + 1)] if start_date and end_date else sorted(daily_map.values())
                
                if len(daily_counts) > 1:
                    spike_info = detect_spike(daily_counts, baseline_days=7)
                    if spike_info['is_spike']:
                        spike_count += 1
            
            # Count active diseases (approximate via keys if not provided)
            total_diseases = len(daily_by_disease) or 1
            adaptive_buffer = calculate_dynamic_safety_buffer(spike_count, total_diseases)
            
            spike_percentage = (spike_count / total_diseases * 100) if total_diseases > 0 else 0
            
            return {
                'adaptive_buffer': round(adaptive_buffer, 3),
                'spike_count': spike_count,
                'total_diseases': total_diseases,
                'spike_percentage': round(spike_percentage, 1),
                'base_buffer': BASE_SAFETY_BUFFER,
                'max_buffer': MAX_SAFETY_BUFFER,
                'interpretation': (
                    'high_risk' if adaptive_buffer >= 1.6 else
                    'medium_risk' if adaptive_buffer >= 1.4 else
                    'low_risk'
                )
            }
        except Exception as e:
            self.logger.error("Adaptive buffer calculation failed", exception=e)
            return {'adaptive_buffer': BASE_SAFETY_BUFFER, 'error': str(e)}

    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 4 + Intelligent Restock Generator
    # Generates comprehensive restock recommendations
    # ────────────────────────────────────────────────────────────────────────────
    
    def calculate_restock_suggestions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        use_adaptive_buffer: bool = True,
        precalculated_context: Optional[Dict] = None,
        request = None
    ) -> List[Dict]:
        """
        FEATURE 4 + 10: Optimized restock suggestions.
        Accepts precalculated context to avoid expensive redundant queries.
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            ctx = precalculated_context or {}
            current_month = date.today().month

            # ──── Step 1: Disease counts and Buffer ────
            if 'daily_by_dtype' in ctx:
                daily_by_dtype = ctx['daily_by_dtype']
                dtype_season = ctx.get('dtype_season', {})
            else:
                appt_qs_base = Appointment.objects.filter(
                    appointment_datetime__date__range=(start_date, end_date), 
                    disease__isnull=False
                )
                appt_qs = apply_clinic_filter(appt_qs_base, request) \
                    .values('appointment_datetime__date', 'disease__name', 'disease__season') \
                    .annotate(day_count=Count('id'))
                daily_by_dtype = defaultdict(lambda: defaultdict(int))
                dtype_season = {}
                for row in appt_qs:
                    dtype = get_disease_type(row['disease__name'])
                    dtype_season[dtype] = row['disease__season']
                    daily_by_dtype[dtype][row['appointment_datetime__date']] += row['day_count']

            # Adaptive buffer (Reuse if in context)
            if use_adaptive_buffer:
                if 'buffer_info' in ctx:
                    safety_buffer = ctx['buffer_info'].get('adaptive_buffer', 0)
                else:
                    buffer_info = self.calculate_adaptive_buffer(start_date, end_date, daily_by_disease=daily_by_dtype, request=request)
                    safety_buffer = buffer_info.get('adaptive_buffer', 0)
            else:
                safety_buffer = BASE_SAFETY_BUFFER

            # ──── Step 2: Medicine usage patterns ────
            # Performance Fix: Identify top medicines first to leverage ID-based indexing
            top_medicines_info = ctx.get('top_medicines_data')
            if not top_medicines_info:
                # 1. Fetch top drugs by ID for index hit
                top_rx_qs_base = PrescriptionLine.objects.filter(prescription_date__range=(start_date, end_date))
                top_drugs_stats = apply_clinic_filter(top_rx_qs_base, request, clinic_field='prescription__clinic') \
                    .values('drug_id') \
                    .annotate(total=Sum('quantity')) \
                    .order_by('-total')[:100]
                top_ids = [d['drug_id'] for d in top_drugs_stats]
                
                # 2. Map IDs to Names/Stock in one go
                dm_qs_base = DrugMaster.objects.filter(id__in=top_ids)
                top_drug_objs = apply_clinic_filter(dm_qs_base, request).values('id', 'drug_name')
                top_medicines_info = {d['id']: d['drug_name'] for d in top_drug_objs}

            top_ids = list(top_medicines_info.keys())
            
            # 3. Optimized ID-Based Query (Leverages Composite Index)
            qty_qs_base = PrescriptionLine.objects.filter(
                prescription_date__range=(start_date, end_date),
                drug_id__in=top_ids,
                disease__isnull=False
            )
            qty_qs = apply_clinic_filter(qty_qs_base, request, clinic_field='prescription__clinic') \
                .values('drug_id', 'disease__name') \
                .annotate(total_qty=Sum('quantity'))
            
            drug_qty_map = defaultdict(int)
            drug_cases_map = defaultdict(int)
            drug_disease_map = defaultdict(set)
            
            # Map of total cases per disease for avg usage calc
            disease_case_map = {dtype: sum(day_map.values()) for dtype, day_map in daily_by_dtype.items()}

            for row in qty_qs:
                drug_name = top_medicines_info.get(row['drug_id'], "Unknown")
                dtype = get_disease_type(row['disease__name'])
                drug_qty_map[drug_name] += row['total_qty'] or 0
                drug_cases_map[drug_name] += disease_case_map.get(dtype, 1)
                drug_disease_map[drug_name].add(dtype)
            
            avg_usage_map = {drug: round(drug_qty_map[drug] / max(drug_cases_map[drug], 1), 4) for drug in drug_qty_map}
            
            # ──── Step 3: Disease demand forecasts ────
            dtype_demand = ctx.get('dtype_demand', {})
            if not dtype_demand:
                for dtype, daily_map in daily_by_dtype.items():
                    daily = [daily_map.get(start_date + timedelta(days=i), 0) for i in range((end_date - start_date).days + 1)]
                    forecast = moving_average_forecast(daily)
                    trend = weighted_trend_score(sum(daily[-7:]), sum(daily[:-7]) if len(daily) > 7 else 0)
                    demand = predict_demand(trend, forecast)
                    sw = get_seasonal_weight(dtype_season.get(dtype, 'All'), current_month)
                    dtype_demand[dtype] = {'demand': demand, 'seasonal_weight': sw}
            
            # ──── Step 4: Calculate restock for selected drugs ────
            top_names = list(top_medicines_info.values())
            stock_qs_base = DrugMaster.objects.filter(drug_name__in=top_names)
            stock_qs = apply_clinic_filter(stock_qs_base, request) \
                .values('drug_name') \
                .annotate(total_stock=Sum('current_stock'))
            stock_map = {r['drug_name']: r['total_stock'] for r in stock_qs}
            
            results = []
            for drug_name in top_names:
                current_stock = stock_map.get(drug_name, 0) or 0
                avg_usage = avg_usage_map.get(drug_name, 1.0)
                contributing = list(drug_disease_map.get(drug_name, set()))
                if not contributing: contributing = list(dtype_demand.keys())[:5]
                
                disease_demands = [{'predicted_demand': dtype_demand[d]['demand'], 'seasonal_weight': dtype_demand[d]['seasonal_weight']} 
                                  for d in contributing if d in dtype_demand]
                combined = apply_multi_disease_contribution(disease_demands) if disease_demands else 0.0
                
                results.append(calculate_restock(drug_name=drug_name, generic_name='', predicted_demand=combined,
                                              avg_usage=avg_usage, current_stock=current_stock,
                                              contributing_diseases=contributing, safety_buffer=safety_buffer))
            
            results.sort(key=lambda x: ({'critical': 0, 'low': 1, 'sufficient': 2}.get(x['status'], 3), -x['suggested_restock']))
            return results
        except Exception as e:
            self.logger.error("Restock calculation failed", exception=e)
            return []

    
    def get_district_restock(
        self,
        district: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get district-level restock recommendations.
        
        For new users: Aggregates restock needs across all clinics
        in a district for centralized procurement.
        
        Args:
            district: District name
            start_date: Period start
            end_date: Period end
        
        Returns:
            District restock summary with per-drug recommendations
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
           # Get all drugs in district
            drugs_in_district = (
                DrugMaster.objects
                .filter(clinic__clinic_address_1__icontains=district)
                .select_related('clinic')
                .values(
                    'drug_name', 'generic_name', 'drug_strength', 'dosage_type',
                    'clinic__id'
                )
                .annotate(stock=Sum('current_stock'))
            )
            
            district_drugs = {}
            for drug in drugs_in_district:
                key = (
                    drug['drug_name'],
                    drug['generic_name'],
                    drug['drug_strength'],
                    drug['dosage_type']
                )
                district_drugs[key] = district_drugs.get(key, 0) + (drug['stock'] or 0)
            
            # Get system-wide forecasts and apply district ratio
            system_suggestions = self.calculate_restock_suggestions(
                start_date, end_date
            )
            
            district_results = []
            total_clinics = Clinic.objects.count() or 1
            
            for suggestion in system_suggestions:
                # Find matching district drugs
                for (drug_name, generic, strength, dosage), stock in district_drugs.items():
                    if drug_name == suggestion['drug_name']:
                        # Pro-rate system demand to district
                        district_ratio = 0.5  # Placeholder
                        district_demand = suggestion['predicted_demand'] * district_ratio
                        
                        district_results.append({
                            'drug_name': drug_name,
                            'generic_name': generic,
                            'strength': strength,
                            'dosage_type': dosage,
                            'district': district,
                            'current_stock': stock,
                            'predicted_demand': round(district_demand, 1),
                            'suggested_restock': max(0, int(district_demand - stock)),
                            'status': suggestion['status']
                        })
            
            return {
                'district': district,
                'period': f'{start_date} to {end_date}',
                'total_drugs': len(district_results),
                'results': sorted(
                    district_results,
                    key=lambda x: -x['suggested_restock']
                )
            }
        
        except Exception as e:
            self.logger.error(
                "District restock retrieval failed for %s",
                district,
                exception=e
            )
            return {'error': str(e)}
