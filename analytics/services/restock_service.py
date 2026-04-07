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
from ..aggregation import get_disease_type
from ..ml_engine import (
    moving_average_forecast,
    weighted_trend_score,
    predict_demand
)
from ..restock_calculator import (
    calculate_restock,
    calculate_dynamic_safety_buffer,
    apply_multi_disease_contribution,
    BASE_SAFETY_BUFFER,
    MAX_SAFETY_BUFFER
)
from ..spike_detector import get_seasonal_weight, detect_spike
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
        end_date: Optional[date] = None
    ) -> Dict:
        """
        FEATURE 5: Calculate adaptive safety buffer based on current spike situation.
        
        Formula:
            buffer = 1.2 + (spike_ratio × 0.6)
            where spike_ratio = detected_spikes / total_active_diseases
        
        Higher spike activity increases buffer:
        - No spikes: buffer = 1.2 (20% extra stock)
        - 50% of diseases spiking: buffer = 1.5 (50% extra)
        - All diseases spiking: buffer = 1.8 (80% extra)
        
        For new users: Automatically adjusts reorder quantities based on
        system-wide outbreak risk. Prevents stockouts during emergencies.
        
        Args:
            start_date: Analysis period start
            end_date: Analysis period end
        
        Returns:
            Dictionary with buffer calculation details:
                - adaptive_buffer: Calculated buffer (1.2-1.8)
                - spike_count: Number of detected spikes
                - total_diseases: Total active diseases
                - spike_percentage: % of diseases with spikes
        
        Example:
            buffer_info = service.calculate_adaptive_buffer()
            print(f"Use buffer: {buffer_info['adaptive_buffer']}")
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Count active diseases
            active_diseases = (
                Disease.objects
                .filter(is_active=True)
                .values('name')
                .distinct()
                .count()
            )
            
            if active_diseases == 0:
                active_diseases = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        disease__isnull=False
                    )
                    .values('disease')
                    .distinct()
                    .count()
                )
            
            # Count spikes
            qs = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__isnull=False
                )
                .select_related('disease')
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('appt_date', 'disease__name')
                .annotate(day_count=Count('id'))
                .order_by('disease__name', 'appt_date')
            )
            
            daily_by_disease = defaultdict(lambda: defaultdict(int))
            for row in qs:
                disease = get_disease_type(row['disease__name'])
                daily_by_disease[disease][row['appt_date']] += row['day_count']
            
            spike_count = 0
            for disease, daily_map in daily_by_disease.items():
                sorted_dates = sorted(daily_map.keys())
                daily_counts = [daily_map[d] for d in sorted_dates]
                
                if len(daily_counts) > 1:
                    spike_info = detect_spike(daily_counts, baseline_days=7)
                    if spike_info['is_spike']:
                        spike_count += 1
            
            # Calculate adaptive buffer
            total_diseases = max(len(daily_by_disease), active_diseases)
            adaptive_buffer = calculate_dynamic_safety_buffer(spike_count, total_diseases)
            
            spike_percentage = (spike_count / total_diseases * 100) if total_diseases > 0 else 0
            
            result = {
                'adaptive_buffer': round(adaptive_buffer, 3),
                'spike_count': spike_count,
                'total_diseases': total_diseases,
                'spike_percentage': round(spike_percentage, 1),
                'base_buffer': BASE_SAFETY_BUFFER,
                'max_buffer': MAX_SAFETY_BUFFER,
                'buffer_increase': round(adaptive_buffer - BASE_SAFETY_BUFFER, 3),
                'interpretation': (
                    'high_risk' if adaptive_buffer >= 1.6 else
                    'medium_risk' if adaptive_buffer >= 1.4 else
                    'low_risk'
                )
            }
            
            self.logger.info(
                "Adaptive buffer calculated: %.3f (spikes: %d, diseases: %d)",
                adaptive_buffer, spike_count, total_diseases
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Adaptive buffer calculation failed",
                exception=e
            )
            return {
                'adaptive_buffer': BASE_SAFETY_BUFFER,
                'error': str(e)
            }
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 4 + Intelligent Restock Generator
    # Generates comprehensive restock recommendations
    # ────────────────────────────────────────────────────────────────────────────
    
    def calculate_restock_suggestions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        use_adaptive_buffer: bool = True
    ) -> List[Dict]:
        """
        FEATURE 4 + 10: Calculate restock suggestions for all medicines.
        
        Combines:
        - Historical usage patterns
        - Active disease forecasts
        - Current stock levels
        - Adaptive safety buffer (if enabled)
        
        For new users: Intelligent recommendations prevent stockouts
        and reduce excess inventory. Prioritizes by urgency.
        
        Args:
            start_date: Historical analysis period start
            end_date: Historical analysis period end
            use_adaptive_buffer: Whether to apply dynamic buffer adjustment
        
        Returns:
            List of restock recommendations sorted by urgency:
                - critical: immediate action required
                - low: order soon
                - sufficient: adequate stock
        
        Example:
            suggestions = service.calculate_restock_suggestions()
            critical = [s for s in suggestions if s['status'] == 'critical']
            for med in critical:
                place_urgent_order(med)
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            current_month = date.today().month
            mid = start_date + (end_date - start_date) // 2
            
            # Get adaptive buffer if enabled
            if use_adaptive_buffer:
                buffer_info = self.calculate_adaptive_buffer(start_date, end_date)
                safety_buffer = buffer_info['adaptive_buffer']
            else:
                safety_buffer = BASE_SAFETY_BUFFER
            
            # ──── Step 1: Disease case counts and predictions ────
            appt_qs = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__isnull=False
                )
                .select_related('disease')
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('appt_date', 'disease__name', 'disease__season')
                .annotate(day_count=Count('id'))
            )
            
            daily_by_dtype = defaultdict(lambda: defaultdict(int))
            dtype_season = {}
            
            for row in appt_qs:
                dtype = get_disease_type(row['disease__name'])
                dtype_season[dtype] = row['disease__season']
                daily_by_dtype[dtype][row['appt_date']] += row['day_count']
            
            # ──── Step 2: Medicine usage patterns ────
            qty_qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__range=(start_date, end_date),
                    disease__isnull=False
                )
                .select_related('drug', 'disease')
                .values('drug__drug_name', 'disease__name')
                .annotate(total_qty=Sum('quantity'))
            )
            
            disease_case_map = defaultdict(int)
            for dtype, day_map in daily_by_dtype.items():
                disease_case_map[dtype] = sum(day_map.values())
            
            drug_qty_map = defaultdict(int)
            drug_cases_map = defaultdict(int)
            drug_disease_map = defaultdict(set)
            
            for row in qty_qs:
                drug_name = row['drug__drug_name']
                dtype = get_disease_type(row['disease__name'])
                drug_qty_map[drug_name] += row['total_qty'] or 0
                drug_cases_map[drug_name] += disease_case_map.get(dtype, 1)
                drug_disease_map[drug_name].add(dtype)
            
            avg_usage_map = {
                drug: round(drug_qty_map[drug] / max(drug_cases_map[drug], 1), 4)
                for drug in drug_qty_map
            }
            
            # ──── Step 3: Disease demand forecasts ────
            dtype_demand = {}
            for dtype in dtype_season:
                daily = [
                    daily_by_dtype[dtype].get(
                        start_date + timedelta(days=i),
                        0
                    )
                    for i in range((end_date - start_date).days + 1)
                ]
                
                forecast = moving_average_forecast(daily)
                trend = weighted_trend_score(
                    sum(daily[-7:]),
                    sum(daily[:-7]) if len(daily) > 7 else 0
                )
                demand = predict_demand(trend, forecast)
                sw = get_seasonal_weight(dtype_season[dtype], current_month)
                
                dtype_demand[dtype] = {
                    'demand': demand,
                    'seasonal_weight': sw
                }
            
            # ──── Step 4: Calculate restock for all drugs ────
            stock_map = {
                r['drug_name']: r['total_stock']
                for r in DrugMaster.objects
                .values('drug_name')
                .annotate(total_stock=Sum('current_stock'))
            }
            
            all_drug_names = set(stock_map.keys()) | set(drug_qty_map.keys())
            results = []
            
            for drug_name in all_drug_names:
                current_stock = stock_map.get(drug_name, 0) or 0
                avg_usage = avg_usage_map.get(drug_name, 1.0) or 1.0
                contributing = list(drug_disease_map.get(drug_name, set()))
                
                if not contributing:
                    contributing = list(dtype_demand.keys())[:5]
                
                disease_demands = [
                    {
                        'predicted_demand': dtype_demand[d]['demand'],
                        'seasonal_weight': dtype_demand[d]['seasonal_weight']
                    }
                    for d in contributing if d in dtype_demand
                ]
                
                combined = (
                    apply_multi_disease_contribution(disease_demands)
                    if disease_demands else 0.0
                )
                
                suggestion = calculate_restock(
                    drug_name=drug_name,
                    generic_name='',
                    predicted_demand=combined,
                    avg_usage=avg_usage,
                    current_stock=current_stock,
                    contributing_diseases=contributing,
                    safety_buffer=safety_buffer
                )
                
                results.append(suggestion)
            
            # Sort by status and restock quantity
            STATUS_ORDER = {'critical': 0, 'low': 1, 'sufficient': 2}
            results.sort(key=lambda x: (
                STATUS_ORDER.get(x['status'], 3),
                -x['suggested_restock']
            ))
            
            self.logger.info(
                "Generated %d restock suggestions (buffer: %.3f)",
                len(results), safety_buffer
            )
            
            return results
        
        except Exception as e:
            self.logger.error(
                "Restock suggestion calculation failed",
                exception=e
            )
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
