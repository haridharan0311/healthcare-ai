"""
Prediction Engine - Layer 3: ML-Based Forecasting

This engine provides predictive analytics capabilities:
- Disease outbreak forecasting
- Medicine demand prediction
- Stock depletion forecasting
- Trend extrapolation
- Seasonal pattern prediction

For new users: This engine uses historical data to predict future
healthcare needs, helping with proactive planning and resource allocation.
"""

import logging
import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate

from analytics.models import Appointment, Disease
from inventory.models import DrugMaster, PrescriptionLine
from core.models import Clinic

from .aggregation import get_disease_type, build_daily_list
from .ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class PredictionEngine:
    """
    Prediction engine for healthcare forecasting.
    
    This engine uses statistical methods and machine learning to predict:
    - Future disease cases
    - Medicine demand
    - Stock requirements
    - Resource needs
    
    Usage:
        engine = PredictionEngine()
        
        # Predict disease outbreaks
        outbreak_forecast = engine.predict_disease_outbreaks(days_ahead=14)
        
        # Predict medicine demand
        demand_forecast = engine.predict_medicine_demand(days_ahead=30)
        
        # Get comprehensive forecast
        forecast = engine.get_forecast_dashboard()
    """
    
    def __init__(self):
        """Initialize the prediction engine."""
        self.logger = logger
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DISEASE OUTBREAK PREDICTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def predict_disease_outbreaks(
        self,
        days_ahead: int = 14,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        confidence_threshold: float = 0.7
    ) -> Dict:
        """
        Predict potential disease outbreaks.
        
        For new users: This analysis identifies diseases that are likely to
        spike in the coming days/weeks, allowing for proactive resource
        allocation and preventive measures.
        
        Args:
            days_ahead: Number of days to forecast ahead
            start_date: Historical analysis period start
            end_date: Historical analysis period end
            confidence_threshold: Minimum confidence for alerts (0-1)
            
        Returns:
            Dictionary containing:
                - outbreak_alerts: Diseases predicted to spike
                - disease_forecasts: Detailed forecasts for each disease
                - confidence_scores: Prediction confidence levels
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range(days_back=60)
            
            # Get daily disease counts
            disease_qs = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__isnull=False
                )
                .select_related('disease')
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('appt_date', 'disease__name', 'disease__season', 
                       'disease__severity')
                .annotate(daily_count=Count('id'))
                .order_by('disease__name', 'appt_date')
            )
            
            # Build time series for each disease
            disease_series = defaultdict(lambda: {
                'daily_counts': defaultdict(int),
                'season': 'All',
                'severity': 1
            })
            
            for row in disease_qs:
                dtype = get_disease_type(row['disease__name'])
                disease_series[dtype]['daily_counts'][row['appt_date']] = row['daily_count']
                disease_series[dtype]['season'] = row['disease__season']
                disease_series[dtype]['severity'] = row['disease__severity']
            
            # Generate forecasts for each disease
            outbreak_alerts = []
            disease_forecasts = []
            
            current_month = date.today().month
            
            for dtype, data in disease_series.items():
                # Build ordered daily list
                daily_list = build_daily_list(
                    data['daily_counts'], start_date, end_date
                )
                
                if len(daily_list) < 7:
                    continue  # Not enough data
                
                # Calculate forecast metrics
                forecast = moving_average_forecast(daily_list)
                recent_sum = sum(daily_list[-7:])
                older_sum = sum(daily_list[:-7]) if len(daily_list) > 7 else 0
                trend_score = weighted_trend_score(recent_sum, older_sum)
                predicted_demand = predict_demand(trend_score, forecast)
                
                # Apply seasonal weight
                seasonal_weight = self._get_seasonal_weight(
                    data['season'], current_month
                )
                adjusted_demand = predicted_demand * seasonal_weight
                
                # Calculate confidence based on data quality
                data_points = len([d for d in daily_list if d > 0])
                data_quality = min(data_points / len(daily_list), 1.0)
                consistency = 1.0 - (self._calculate_coefficient_of_variation(daily_list) / 100)
                confidence = round((data_quality * 0.4 + consistency * 0.6), 2)
                
                # Determine if this is an outbreak alert
                avg_daily = sum(daily_list) / len(daily_list) if daily_list else 0
                outbreak_threshold = avg_daily * 2.0  # 2x normal rate
                
                is_outbreak = (
                    adjusted_demand > outbreak_threshold and
                    confidence >= confidence_threshold
                )
                
                forecast_data = {
                    'disease_name': dtype,
                    'season': data['season'],
                    'severity': data['severity'],
                    'current_avg_daily': round(avg_daily, 2),
                    'predicted_daily': round(adjusted_demand, 2),
                    'forecast_demand_14_days': round(adjusted_demand * days_ahead, 0),
                    'trend_score': trend_score,
                    'seasonal_weight': seasonal_weight,
                    'confidence': confidence,
                    'data_quality': round(data_quality, 2),
                    'trend_direction': 'up' if trend_score > avg_daily * 7 else 'down' if trend_score < avg_daily * 7 else 'stable'
                }
                
                disease_forecasts.append(forecast_data)
                
                if is_outbreak:
                    outbreak_alerts.append({
                        'disease_name': dtype,
                        'severity': data['severity'],
                        'predicted_increase': round(
                            ((adjusted_demand - avg_daily) / max(avg_daily, 1)) * 100, 1
                        ),
                        'confidence': confidence,
                        'predicted_peak_date': str(end_date + timedelta(days=7)),  # Estimated peak
                        'recommended_action': self._get_outbreak_recommendation(
                            data['severity'], adjusted_demand, avg_daily
                        )
                    })
            
            # Sort by severity and confidence
            outbreak_alerts.sort(key=lambda x: (-x['severity'], -x['confidence']))
            disease_forecasts.sort(key=lambda x: -x['predicted_demand_14_days'])
            
            return {
                'forecast_period': f'{end_date} to {end_date + timedelta(days=days_ahead)}',
                'historical_period': f'{start_date} to {end_date}',
                'total_diseases_analyzed': len(disease_forecasts),
                'outbreak_alerts': outbreak_alerts,
                'disease_forecasts': disease_forecasts,
                'summary': {
                    'high_risk_outbreaks': len([a for a in outbreak_alerts if a['severity'] >= 3]),
                    'medium_risk_outbreaks': len([a for a in outbreak_alerts if a['severity'] == 2]),
                    'low_risk_outbreaks': len([a for a in outbreak_alerts if a['severity'] == 1])
                }
            }
            
        except Exception as e:
            self.logger.error("Disease outbreak prediction failed: %s", str(e))
            return {
                'error': str(e),
                'outbreak_alerts': [],
                'disease_forecasts': []
            }
    
    def _get_seasonal_weight(self, season: str, current_month: int) -> float:
        """Get seasonal adjustment weight."""
        season_month_map = {
            'Winter': [12, 1, 2],
            'Spring': [3, 4, 5],
            'Summer': [6, 7, 8],
            'Fall': [9, 10, 11],
            'Monsoon': [6, 7, 8, 9],
            'All': list(range(1, 13))
        }
        
        months = season_month_map.get(season, list(range(1, 13)))
        if current_month in months:
            return 1.2  # In season - higher weight
        else:
            return 0.8  # Off season - lower weight
    
    def _calculate_coefficient_of_variation(self, data: List[int]) -> float:
        """Calculate coefficient of variation (CV) for data consistency."""
        if not data or len(data) < 2:
            return 0.0
        
        mean = sum(data) / len(data)
        if mean == 0:
            return 0.0
        
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std_dev = math.sqrt(variance)
        
        return (std_dev / mean) * 100
    
    def _get_outbreak_recommendation(self, severity: int, predicted: float, avg: float) -> str:
        """Get recommended action based on outbreak severity."""
        increase_pct = ((predicted - avg) / max(avg, 1)) * 100
        
        if severity >= 4 or increase_pct > 200:
            return "URGENT: Prepare emergency response, increase staffing, stockpile critical supplies"
        elif severity >= 3 or increase_pct > 100:
            return "HIGH: Increase surveillance, prepare additional resources, alert healthcare workers"
        elif severity >= 2 or increase_pct > 50:
            return "MODERATE: Monitor closely, ensure adequate supplies, review protocols"
        else:
            return "LOW: Continue routine monitoring, maintain standard precautions"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEDICINE DEMAND PREDICTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def predict_medicine_demand(
        self,
        days_ahead: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Predict medicine demand for the upcoming period.
        
        For new users: This forecast helps ensure adequate medicine stock
        by predicting which medicines will be in high demand based on
        disease patterns and historical usage.
        
        Args:
            days_ahead: Number of days to forecast ahead
            start_date: Historical analysis period start
            end_date: Historical analysis period end
            
        Returns:
            Dictionary containing:
                - demand_forecasts: Predicted demand for each medicine
                - critical_medicines: Medicines that need immediate attention
                - stock_recommendations: Suggested stock levels
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range(days_back=90)
            
            # Get medicine usage history
            usage_qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__range=(start_date, end_date),
                    drug__isnull=False
                )
                .select_related('drug')
                .annotate(rx_date=TruncDate('prescription_date'))
                .values('rx_date', 'drug__drug_name', 'drug__generic_name',
                       'drug__drug_strength', 'drug__dosage_type')
                .annotate(daily_qty=Sum('quantity'))
                .order_by('drug__drug_name', 'rx_date')
            )
            
            # Build time series for each medicine
            medicine_series = defaultdict(lambda: {
                'daily_quantities': defaultdict(int),
                'generic_name': '',
                'strength': '',
                'dosage_type': ''
            })
            
            for row in usage_qs:
                drug_name = row['drug__drug_name']
                medicine_series[drug_name]['daily_quantities'][row['rx_date']] = row['daily_qty']
                medicine_series[drug_name]['generic_name'] = row['drug__generic_name'] or ''
                medicine_series[drug_name]['strength'] = row['drug__drug_strength']
                medicine_series[drug_name]['dosage_type'] = row['drug__dosage_type']
            
            # Get current stock levels
            stock_map = {}
            for drug in DrugMaster.objects.values('drug_name', 'current_stock'):
                stock_map[drug['drug_name']] = drug['current_stock']
            
            # Generate forecasts
            demand_forecasts = []
            critical_medicines = []
            
            for drug_name, data in medicine_series.items():
                daily_list = build_daily_list(
                    data['daily_quantities'], start_date, end_date
                )
                
                if len(daily_list) < 7:
                    continue
                
                # Calculate forecast
                forecast = moving_average_forecast(daily_list)
                recent_sum = sum(daily_list[-7:])
                older_sum = sum(daily_list[:-7]) if len(daily_list) > 7 else 0
                trend_score = weighted_trend_score(recent_sum, older_sum)
                predicted_daily = predict_demand(trend_score, forecast)
                
                # Calculate total demand for forecast period
                total_predicted_demand = predicted_daily * days_ahead
                
                # Get current stock
                current_stock = stock_map.get(drug_name, 0)
                
                # Calculate days of stock remaining
                days_of_stock = current_stock / predicted_daily if predicted_daily > 0 else 999
                
                # Determine if critical
                is_critical = days_of_stock < days_ahead * 0.5  # Less than 50% of forecast period
                
                forecast_data = {
                    'drug_name': drug_name,
                    'generic_name': data['generic_name'],
                    'strength': data['strength'],
                    'dosage_type': data['dosage_type'],
                    'current_stock': current_stock,
                    'predicted_daily_demand': round(predicted_daily, 2),
                    'total_predicted_demand': round(total_predicted_demand, 0),
                    'days_of_stock': round(days_of_stock, 1),
                    'trend_direction': 'up' if trend_score > sum(daily_list[-7:]) else 'down' if trend_score < sum(daily_list[-7:]) else 'stable',
                    'recommended_stock': round(total_predicted_demand * 1.2, 0),  # 20% buffer
                    'reorder_quantity': max(0, round(total_predicted_demand * 1.2 - current_stock, 0))
                }
                
                demand_forecasts.append(forecast_data)
                
                if is_critical:
                    critical_medicines.append({
                        'drug_name': drug_name,
                        'generic_name': data['generic_name'],
                        'current_stock': current_stock,
                        'days_of_stock': round(days_of_stock, 1),
                        'urgency': 'critical' if days_of_stock < 7 else 'high',
                        'recommended_action': f"Order {forecast_data['reorder_quantity']} units immediately"
                    })
            
            # Sort by urgency
            critical_medicines.sort(key=lambda x: x['days_of_stock'])
            demand_forecasts.sort(key=lambda x: -x['total_predicted_demand'])
            
            return {
                'forecast_period': f'{end_date} to {end_date + timedelta(days=days_ahead)}',
                'historical_period': f'{start_date} to {end_date}',
                'total_medicines_analyzed': len(demand_forecasts),
                'demand_forecasts': demand_forecasts[:50],  # Top 50
                'critical_medicines': critical_medicines,
                'summary': {
                    'critical_count': len([m for m in critical_medicines if m['urgency'] == 'critical']),
                    'high_priority_count': len([m for m in critical_medicines if m['urgency'] == 'high']),
                    'total_reorder_value': sum(m['reorder_quantity'] for m in demand_forecasts)
                }
            }
            
        except Exception as e:
            self.logger.error("Medicine demand prediction failed: %s", str(e))
            return {
                'error': str(e),
                'demand_forecasts': [],
                'critical_medicines': []
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CLINIC RESOURCE PREDICTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def predict_clinic_resource_needs(
        self,
        days_ahead: int = 14,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Predict resource needs for each clinic.
        
        For new users: This helps clinic managers plan staffing,
        supplies, and other resources based on predicted patient volume.
        
        Args:
            days_ahead: Number of days to forecast ahead
            start_date: Historical analysis period start
            end_date: Historical analysis period end
            
        Returns:
            Resource predictions per clinic
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range(days_back=60)
            
            # Get clinic-wise appointment data
            clinic_qs = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    clinic__isnull=False
                )
                .select_related('clinic')
                .annotate(appt_date=TruncDate('appointment_datetime'))
                .values('clinic__id', 'clinic__clinic_name', 'appt_date')
                .annotate(daily_count=Count('id'))
                .order_by('clinic__clinic_name', 'appt_date')
            )
            
            # Build time series for each clinic
            clinic_series = defaultdict(lambda: defaultdict(int))
            clinic_names = {}
            
            for row in clinic_qs:
                clinic_id = row['clinic__id']
                clinic_series[clinic_id][row['appt_date']] = row['daily_count']
                clinic_names[clinic_id] = row['clinic__clinic_name']
            
            # Generate forecasts for each clinic
            clinic_forecasts = []
            
            for clinic_id, daily_map in clinic_series.items():
                daily_list = build_daily_list(daily_map, start_date, end_date)
                
                if len(daily_list) < 7:
                    continue
                
                # Calculate forecast
                forecast = moving_average_forecast(daily_list)
                recent_sum = sum(daily_list[-7:])
                older_sum = sum(daily_list[:-7]) if len(daily_list) > 7 else 0
                trend_score = weighted_trend_score(recent_sum, older_sum)
                predicted_daily = predict_demand(trend_score, forecast)
                
                avg_daily = sum(daily_list) / len(daily_list) if daily_list else 0
                
                clinic_forecasts.append({
                    'clinic_id': clinic_id,
                    'clinic_name': clinic_names[clinic_id],
                    'current_avg_daily_patients': round(avg_daily, 1),
                    'predicted_daily_patients': round(predicted_daily, 1),
                    'predicted_total_patients': round(predicted_daily * days_ahead, 0),
                    'trend_direction': 'up' if predicted_daily > avg_daily else 'down' if predicted_daily < avg_daily else 'stable',
                    'resource_recommendations': {
                        'staff_needed': max(1, round(predicted_daily / 15, 0)),  # 1 staff per 15 patients
                        'consultation_rooms': max(1, round(predicted_daily / 25, 0)),  # 1 room per 25 patients
                        'estimated_medicine_cost': round(predicted_daily * days_ahead * 50, 2)  # Estimated cost
                    }
                })
            
            # Sort by predicted patient volume
            clinic_forecasts.sort(key=lambda x: -x['predicted_daily_patients'])
            
            return {
                'forecast_period': f'{end_date} to {end_date + timedelta(days=days_ahead)}',
                'clinics_analyzed': len(clinic_forecasts),
                'clinic_forecasts': clinic_forecasts,
                'total_predicted_patients': sum(c['predicted_total_patients'] for c in clinic_forecasts)
            }
            
        except Exception as e:
            self.logger.error("Clinic resource prediction failed: %s", str(e))
            return {
                'error': str(e),
                'clinic_forecasts': []
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FORECAST DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_forecast_dashboard(self, days_ahead: int = 14) -> Dict:
        """
        Get comprehensive forecasting dashboard.
        
        For new users: This provides a single view of all predictions -
        disease outbreaks, medicine demand, and resource needs.
        
        Args:
            days_ahead: Number of days to forecast ahead
            
        Returns:
            Comprehensive forecast dashboard
        """
        # Get all forecasts
        outbreak_forecast = self.predict_disease_outbreaks(days_ahead=days_ahead)
        medicine_forecast = self.predict_medicine_demand(days_ahead=days_ahead)
        resource_forecast = self.predict_clinic_resource_needs(days_ahead=days_ahead)
        
        return {
            'generated_at': date.today().isoformat(),
            'forecast_period': f"Next {days_ahead} days",
            'disease_surveillance': {
                'outbreak_alerts': outbreak_forecast.get('outbreak_alerts', []),
                'high_risk_count': outbreak_forecast.get('summary', {}).get('high_risk_outbreaks', 0),
                'total_diseases_tracked': outbreak_forecast.get('total_diseases_analyzed', 0)
            },
            'medicine_inventory': {
                'critical_medicines': medicine_forecast.get('critical_medicines', []),
                'critical_count': medicine_forecast.get('summary', {}).get('critical_count', 0),
                'total_medicines_tracked': medicine_forecast.get('total_medicines_analyzed', 0),
                'total_reorder_value': medicine_forecast.get('summary', {}).get('total_reorder_value', 0)
            },
            'resource_planning': {
                'clinic_forecasts': resource_forecast.get('clinic_forecasts', []),
                'total_predicted_patients': resource_forecast.get('total_predicted_patients', 0),
                'clinics_tracked': resource_forecast.get('clinics_analyzed', 0)
            },
            'action_items': {
                'urgent_outbreaks': len([
                    a for a in outbreak_forecast.get('outbreak_alerts', [])
                    if a.get('severity', 0) >= 4
                ]),
                'critical_stock_items': medicine_forecast.get('summary', {}).get('critical_count', 0),
                'high_volume_clinics': len([
                    c for c in resource_forecast.get('clinic_forecasts', [])
                    if c['predicted_daily_patients'] > 50
                ])
            }
        }