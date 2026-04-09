"""
Medicine Analytics Service Module

Provides comprehensive medicine analysis including:
1. Medicine Dependency Mapping - which medicines used for each disease
2. Top Medicines Report - most used medicines
3. Stock Depletion Forecast - predicts stock depletion based on usage
4. Low Stock Alerts - identifies critical stock situations

Layer: Services (Business Logic)
Dependencies: aggregation, inventory models, logger

Usage:
    from analytics.services.medicine_analytics import MedicineAnalyticsService
    
    service = MedicineAnalyticsService()
    
    # Map medicines to diseases
    dependencies = service.map_medicine_dependencies("Flu")
    
    # Get top medicines
    top = service.get_top_medicines(limit=10, days=30)
    
    # Forecast stock depletion
    forecast = service.forecast_stock_depletion(
        drug_id=5,
        confidence=0.95
    )
"""

import re
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

from django.db.models import Count, Avg, Max, Sum, Q
from django.db.models.functions import TruncDate

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from ..aggregation import get_disease_type
from ..ml_engine import moving_average_forecast
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range, validate_positive_int

logger = get_logger(__name__)


class MedicineAnalyticsService:
    """
    Service for all medicine-related analytics.
    
    For new users: Analyzes medicine usage patterns, predicts stock needs,
    and identifies cost optimization opportunities.
    """
    
    def __init__(self):
        """Initialize service."""
        self.logger = logger
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 3: Medicine Dependency Mapping
    # Analyzes which medicines are most commonly used for each disease
    # ────────────────────────────────────────────────────────────────────────────
    
    def map_medicine_dependencies(
        self,
        disease_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_usage: int = 0
    ) -> Dict or List[Dict]:
        """
        FEATURE 3: Map medicine-to-disease relationships.
        
        For each disease, shows:
        - Which medicines are prescribed
        - Frequency of each medicine
        - Average quantity per prescription
        - Cost implications (potential optimization)
        
        For new users: Helps understand treatment patterns. Consistent
        mappings enable inventory planning based on disease forecasts.
        
        Args:
            disease_name: Specific disease (None = all diseases)
            start_date: Period start
            end_date: Period end
            min_usage: Minimum prescriptions to include (filters noise)
        
        Returns:
            If disease_name: Medicines for that disease
            If disease_name=None: All disease-medicine mappings
        
        Example:
            # Single disease
            flu_meds = service.map_medicine_dependencies("Flu")
            for med in flu_meds['medicines']:
                print(f"{med['drug_name']}: {med['prescriptions']} prescriptions")
            
            # All mappings
            all_maps = service.map_medicine_dependencies()
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            if disease_name:
                # Single disease analysis
                qs = (
                    PrescriptionLine.objects
                    .filter(
                        prescription_date__range=(start_date, end_date),
                        disease__name__icontains=disease_name,
                        disease__isnull=False
                    )
                    .select_related('drug', 'disease')
                    .values('drug__drug_name', 'drug__generic_name', 'drug__drug_strength')
                    .annotate(
                        prescriptions=Count('id'),
                        total_quantity=Sum('quantity'),
                        avg_quantity=Avg('quantity')
                    )
                    .order_by('-prescriptions')
                )
                
                medicines = []
                total_prescriptions = 0
                
                for row in qs:
                    count = row['prescriptions']
                    if count >= min_usage:
                        medicines.append({
                            'drug_name': row['drug__drug_name'],
                            'generic_name': row['drug__generic_name'],
                            'strength': row['drug__drug_strength'],
                            'prescriptions': count,
                            'total_quantity': row['total_quantity'] or 0,
                            'avg_quantity_per_rx': round(row['avg_quantity'] or 0, 2),
                            'percentage': 0  # Will calculate below
                        })
                        total_prescriptions += count
                
                # Calculate percentages
                for med in medicines:
                    med['percentage'] = round(
                        med['prescriptions'] / total_prescriptions * 100, 1
                    ) if total_prescriptions > 0 else 0
                
                result = {
                    'disease_name': disease_name,
                    'total_prescriptions': total_prescriptions,
                    'unique_medicines': len(medicines),
                    'medicines': medicines,
                    'period': f'{start_date} to {end_date}'
                }
                
                self.logger.info(
                    "Medicine mapping for %s: %d medicines, %d prescriptions",
                    disease_name, len(medicines), total_prescriptions
                )
                
                return result
            
            else:
                # All diseases - optimize query with select_related and better aggregation
                qs = (
                    PrescriptionLine.objects
                    .filter(
                        prescription_date__range=(start_date, end_date),
                        disease__isnull=False
                    )
                    .select_related('drug', 'disease')
                    .values(
                        'disease__name',
                        'drug__drug_name',
                        'drug__generic_name'
                    )
                    .annotate(
                        prescriptions=Count('id'),
                        total_quantity=Sum('quantity')
                    )
                    .order_by('disease__name', '-prescriptions')  # Add ordering to reduce Python sorting
                )
                
                disease_map = defaultdict(lambda: {
                    'medicines': [],
                    'total_prescriptions': 0
                })
                
                for row in qs:
                    disease = get_disease_type(row['disease__name'])
                    count = row['prescriptions']
                    
                    if count >= min_usage:
                        disease_map[disease]['medicines'].append({
                            'drug_name': row['drug__drug_name'],
                            'generic_name': row['drug__generic_name'],
                            'prescriptions': count,
                            'total_quantity': row['total_quantity'] or 0
                        })
                        disease_map[disease]['total_prescriptions'] += count
                
                results = []
                for disease, data in disease_map.items():
                    if data['total_prescriptions'] >= min_usage:
                        results.append({
                            'disease_name': disease,
                            'total_prescriptions': data['total_prescriptions'],
                            'unique_medicines': len(data['medicines']),
                            'medicines': sorted(
                                data['medicines'],
                                key=lambda x: -x['prescriptions']
                            )[:10]  # Top 10 medicines per disease
                        })
                
                return sorted(
                    results,
                    key=lambda x: -x['total_prescriptions']
                )
        
        except Exception as e:
            self.logger.error(
                "Medicine dependency mapping failed",
                exception=e
            )
            return {} if disease_name else []
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 3b: Top Medicines
    # Identifies most used medicines across all diseases
    # ────────────────────────────────────────────────────────────────────────────
    
    def get_top_medicines(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 20,
        order_by: str = 'quantity'
    ) -> List[Dict]:
        """
        Get top medicines by usage.
        
        For new users: Identifies bestselling/most-prescribed medicines.
        Helps optimize procurement and identify cost-saving opportunities.
        
        Args:
            start_date: Period start
            end_date: Period end
            limit: How many medicines to return (default: 20)
            order_by: 'quantity' or 'prescriptions'
        
        Returns:
            List of top medicine dictionaries
        
        Example:
            top = service.get_top_medicines(limit=10)
            for med in top:
                print(f"{med['drug_name']}: {med['total_quantity']} units prescribed")
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__range=(start_date, end_date),
                    drug__isnull=False
                )
                .select_related('drug')
                .values(
                    'drug__drug_name',
                    'drug__generic_name',
                    'drug__drug_strength'
                )
                .annotate(
                    total_quantity=Sum('quantity'),
                    prescription_count=Count('id'),
                    avg_qty_per_rx=Avg('quantity')
                )
            )
            
            # Sort
            if order_by == 'quantity':
                qs = qs.order_by('-total_quantity')
            else:
                qs = qs.order_by('-prescription_count')
            
            results = []
            for row in qs[:limit]:
                results.append({
                    'drug_name': row['drug__drug_name'],
                    'generic_name': row['drug__generic_name'],
                    'strength': row['drug__drug_strength'],
                    'total_quantity': row['total_quantity'] or 0,
                    'prescription_count': row['prescription_count'] or 0,
                    'avg_qty_per_rx': round(row['avg_qty_per_rx'] or 0, 2)
                })
            
            self.logger.info(
                "Top %d medicines retrieved, ordered by %s",
                len(results), order_by
            )
            
            return results
        
        except Exception as e:
            self.logger.error(
                "Top medicines retrieval failed",
                exception=e
            )
            return []
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 4: Stock Depletion Forecast
    # Predicts how many days current stock will last
    # ────────────────────────────────────────────────────────────────────────────
    
    def forecast_stock_depletion(
        self,
        drug_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        forecast_days: int = 30
    ) -> Dict:
        """
        FEATURE 4: Forecast when medicine stock will be depleted.
        
        Analyzes:
        - Current stock level
        - Historical usage rate
        - Forecasted demand
        - Estimated days of stock remaining
        
        For new users: Predicts stockout dates so you can reorder in time.
        Useful for procurement planning.
        
        Args:
            drug_id: DrugMaster record ID
            start_date: Historical period start
            end_date: Historical period end
            forecast_days: How many days ahead to forecast
        
        Returns:
            Dictionary with stock forecast:
                - days_until_stockout: When stock runs out
                - current_stock: Today's stock level
                - avg_daily_usage: Units used per day
                - recommended_reorder: How many units to order
                - urgency: 'critical', 'high', 'medium', 'low'
        
        Example:
            forecast = service.forecast_stock_depletion(drug_id=5)
            if forecast['urgency'] == 'critical':
                notify_pharmacy_manager(forecast)
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Get drug info
            drug = DrugMaster.objects.filter(id=drug_id).first()
            if not drug:
                self.logger.warning("Drug not found: %s", drug_id)
                return {'error': 'Drug not found'}
            
            current_stock = drug.current_stock or 0
            
            # Calculate historical daily usage
            qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__range=(start_date, end_date),
                    drug_id=drug_id
                )
                .annotate(rx_date=TruncDate('prescription_date'))
                .values('rx_date')
                .annotate(daily_qty=Sum('quantity'))
            )
            
            daily_quantities = [row['daily_qty'] or 0 for row in qs]
            
            if not daily_quantities:
                avg_daily = 1  # Assume 1 unit/day if no history
            else:
                avg_daily = sum(daily_quantities) / len(daily_quantities)
            
            # Calculate days until stockout
            if avg_daily > 0:
                days_until_depletion = current_stock / avg_daily
            else:
                days_until_depletion = float('inf')
            
            # Determine urgency
            if current_stock == 0:
                urgency = 'critical'
            elif days_until_depletion <= 7:
                urgency = 'critical'
            elif days_until_depletion <= 14:
                urgency = 'high'
            elif days_until_depletion <= 30:
                urgency = 'medium'
            else:
                urgency = 'low'
            
            # Calculate recommended reorder
            future_demand = forecast_days * avg_daily * 1.2  # 20% buffer
            recommended_reorder = max(0, int(future_demand - current_stock))
            
            result = {
                'drug_id': drug_id,
                'drug_name': drug.drug_name,
                'generic_name': drug.generic_name,
                'current_stock': current_stock,
                'avg_daily_usage': round(avg_daily, 2),
                'days_until_depletion': round(days_until_depletion, 1) if days_until_depletion != float('inf') else 999,
                'forecast_period_days': forecast_days,
                'estimated_future_demand': round(future_demand, 0),
                'recommended_reorder': recommended_reorder,
                'urgency': urgency,
                'analysis_period': f'{start_date} to {end_date}'
            }
            
            self.logger.info(
                "Stock forecast for %s: %d days until depletion (urgency: %s)",
                drug.drug_name, days_until_depletion, urgency
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Stock depletion forecast failed for drug_id %s",
                drug_id,
                exception=e
            )
            return {'error': str(e)}
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 5: Low Stock Alerts
    # Identifies medicines in critical or low stock situations
    # ────────────────────────────────────────────────────────────────────────────
    
    def get_low_stock_alerts(
        self,
        critical_threshold: int = 10,
        low_threshold: int = 50,
        include_zero: bool = True
    ) -> List[Dict]:
        """
        FEATURE 5 variant: Get all medicines below stock thresholds.
        
        For new users: Identifies medicines that need urgent restocking.
        Helps prevent stockouts that interrupt patient care.
        
        Args:
            critical_threshold: Alert if stock <= this value
            low_threshold: Warning if stock <= this value
            include_zero: Whether to include zero-stock items
        
        Returns:
            List of medicines below thresholds, sorted by urgency
        
        Example:
            alerts = service.get_low_stock_alerts()
            for med in alerts:
                if med['status'] == 'critical':
                    send_urgent_order_email(med)
        """
        try:
            # Get all drugs with stock < critical threshold
            if include_zero:
                drugs = DrugMaster.objects.filter(
                    current_stock__lte=low_threshold
                )
            else:
                drugs = DrugMaster.objects.filter(
                    current_stock__lte=low_threshold,
                    current_stock__gt=0
                )
            
            results = []
            
            for drug in drugs:
                if drug.current_stock == 0:
                    status = 'critical'
                elif drug.current_stock <= critical_threshold:
                    status = 'critical'
                elif drug.current_stock <= low_threshold:
                    status = 'low'
                else:
                    continue
                
                results.append({
                    'drug_id': drug.id,
                    'drug_name': drug.drug_name,
                    'generic_name': drug.generic_name,
                    'strength': drug.drug_strength,
                    'dosage_type': drug.dosage_type,
                    'clinic_name': drug.clinic.clinic_name,
                    'current_stock': drug.current_stock,
                    'status': status,
                    'critical_threshold': critical_threshold,
                    'low_threshold': low_threshold
                })
            
            # Sort by status (critical first) then by stock
            status_order = {'critical': 0, 'low': 1}
            results.sort(key=lambda x: (
                status_order.get(x['status'], 2),
                x['current_stock']
            ))
            
            self.logger.info(
                "Low stock alerts: %d medicines below thresholds",
                len(results)
            )
            
            return results
        
        except Exception as e:
            self.logger.error(
                "Low stock alerts generation failed",
                exception=e
            )
            return []
    
    def get_medicine_usage_trend(
        self,
        drug_id: int,
        days_back: int = 30
    ) -> Dict:
        """
        Get medicine usage trend over time.
        
        Args:
            drug_id: DrugMaster ID
            days_back: Number of days to analyze
        
        Returns:
            Dictionary with usage trend, peak usage, etc.
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            end_date = date.today()
            
            qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__range=(start_date, end_date),
                    drug_id=drug_id
                )
                .annotate(rx_date=TruncDate('prescription_date'))
                .values('rx_date')
                .annotate(daily_qty=Sum('quantity'))
                .order_by('rx_date')
            )
            
            daily_usage = [row['daily_qty'] or 0 for row in qs]
            
            if not daily_usage:
                return {
                    'drug_id': drug_id,
                    'trend': 'no_data',
                    'avg_usage': 0
                }
            
            avg = sum(daily_usage) / len(daily_usage)
            peak = max(daily_usage)
            
            return {
                'drug_id': drug_id,
                'days_analyzed': len(daily_usage),
                'avg_daily_usage': round(avg, 2),
                'peak_usage': peak,
                'min_usage': min(daily_usage),
                'total_usage': sum(daily_usage),
                'trend': 'increasing' if daily_usage[-1] > avg else 'decreasing'
            }
        
        except Exception as e:
            self.logger.error(
                "Medicine usage trend failed for drug_id %s",
                drug_id,
                exception=e
            )
            return {'error': str(e)}
