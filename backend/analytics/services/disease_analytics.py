"""
Disease Analytics Service Module

Provides comprehensive disease analysis including:
1. Disease Growth Rate Indicator - % change in cases over time
2. Early Outbreak Warning System - detects emerging trends
3. Seasonal Pattern Detection - learns disease behavior by season
4. Doctor Performance Insights - analytics on disease cases per doctor
5. Trend comparison across diseases

Layer: Services (Business Logic)
Dependencies: aggregation, ml_engine, spike_detector, logger, validators

Usage:
    from analytics.services.disease_analytics import DiseaseAnalyticsService
    
    service = DiseaseAnalyticsService()
    
    # Calculate disease growth rates
    growth_data = service.calculate_disease_growth_rate(
        disease_name="Flu",
        days_back=30
    )
    
    # Detect early outbreak trends  
    outbreaks = service.detect_early_outbreaks(
        min_days=3,
        growth_threshold=1.25
    )
    
    # Get seasonal patterns
    patterns = service.get_seasonal_patterns(disease_name="Malaria")
    
    # Doctor-wise disease analysis
    doctor_stats = service.get_doctor_disease_insights(
        doctor_id=5
    )
"""

import re
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

from django.db.models import Count, Avg, Max, Sum, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek

from analytics.models import Disease, Appointment
from core.models import Doctor
from ..services.aggregation import get_disease_type
from .ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from .spike_detector import get_seasonal_weight, detect_spike
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range, validate_positive_int

logger = get_logger(__name__)


class DiseaseAnalyticsService:
    """
    Service for all disease-related analytics operations.
    
    For new users: This service wraps database queries and calculations
    related to disease analysis. All methods are stateless and can be called
    independently. Includes caching friendly design.
    """
    
    def __init__(self):
        """Initialize service. No state maintained."""
        self.logger = logger
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 1: Disease Growth Rate Indicator
    # Calculates percentage increase/decrease in disease cases over time periods
    # ────────────────────────────────────────────────────────────────────────────
    
    def calculate_disease_growth_rate(
        self,
        disease_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        comparison_days: int = 7
    ) -> Dict[str, Optional[float]]:
        """
        FEATURE 1: Calculate disease growth rate (percentage change).
        
        Compares case counts in two non-overlapping periods:
        - Recent period: last 'comparison_days'
        - Previous period: similar window before that
        
        Formula: growth_rate = ((recent_count - previous_count) / previous_count) × 100
        
        For new users: Returns percentage growth. Positive = increasing,
        Negative = decreasing, None = insufficient data.
        
        Args:
            disease_name: Name of disease to analyze
            start_date: Analysis start date (default: 30 days ago)
            end_date: Analysis end date (default: today)
            comparison_days: Days in each comparison period (default: 7)
        
        Returns:
            Dictionary with keys:
                - growth_rate: % change (e.g., 25.5 for +25.5%)
                - recent_cases: cases in recent period
                - previous_cases: cases in previous period
                - days_analyzed: Period length
                - status: 'increasing', 'decreasing', or 'stable'
        
        Example:
            result = service.calculate_disease_growth_rate("Flu", comparison_days=7)
            if result['status'] == 'increasing':
                print(f"Alert: Flu cases up {result['growth_rate']}%")
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range(
                    start_date, end_date, max_days=365
                )
            
            # Define comparison periods
            recent_end = end_date
            recent_start = recent_end - timedelta(days=comparison_days)
            
            previous_end = recent_start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=comparison_days)
            
            # Count cases in each period - ORM aggregation
            recent = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(recent_start, recent_end),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .count()
            )
            
            previous = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(previous_start, previous_end),
                    disease__name__icontains=disease_name,
                    disease__isnull=False
                )
                .count()
            )
            
            # Calculate growth rate
            if previous == 0:
                if recent == 0:
                    growth_rate = 0.0
                    status = 'stable'
                else:
                    # Assume 100% growth if previous was 0
                    growth_rate = 100.0
                    status = 'increasing'
            else:
                growth_rate = ((recent - previous) / previous) * 100
                if growth_rate > 10:
                    status = 'increasing'
                elif growth_rate < -10:
                    status = 'decreasing'
                else:
                    status = 'stable'
            
            result = {
                'disease_name': disease_name,
                'growth_rate': round(growth_rate, 2),
                'recent_cases': recent,
                'previous_cases': previous,
                'recent_period': f'{recent_start} to {recent_end}',
                'previous_period': f'{previous_start} to {previous_end}',
                'status': status,
                'days_analyzed': comparison_days
            }
            
            self.logger.info(
                "Growth rate for %s: %.2f%% (%s period)",
                disease_name, growth_rate, comparison_days
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate growth rate for %s",
                disease_name,
                exception=e
            )
            return {
                'growth_rate': None,
                'recent_cases': 0,
                'previous_cases': 0,
                'status': 'unknown',
                'error': str(e)
            }
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 2: Early Outbreak Warning System
    # Detects consistent upward trends in multi-day windows
    # ────────────────────────────────────────────────────────────────────────────
    
    def detect_early_outbreaks(
        self,
        min_cases: int = 5,
        min_days: int = 3,
        growth_threshold: float = 1.2,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        FEATURE 2: Detect early outbreak patterns.
        
        Identifies diseases with:
        1. Consistent upward trend (each day higher than previous)
        2. At least min_days consecutive days of growth
        3. Total growth >= growth_threshold (e.g., 1.2 = 20% increase)
        
        For new users: Returns list of diseases showing outbreak potential.
        Early warning allows proactive resource allocation.
        
        Args:
            min_cases: Minimum daily cases to trigger alert
            min_days: Minimum consecutive days of growth required
            growth_threshold: Multiplier for outbreak detection (1.2 = 20% growth)
            start_date: Analysis period start
            end_date: Analysis period end
        
        Returns:
            List of dictionaries with keys:
                - disease_name: Disease showing outbreak potential
                - trend_days: Number of consecutive growth days
                - first_count: Cases on first day of trend
                - last_count: Cases on last day of trend
                - total_growth: Multiplier (e.g., 1.35 = 35% increase)
                - severity: 'warning' or 'critical'
        
        Example:
            outbreaks = service.detect_early_outbreaks(min_days=3)
            for outbreak in outbreaks:
                if outbreak['severity'] == 'critical':
                    notify_health_ministry(outbreak['disease_name'])
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Fetch all appointments in period with disease info
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
            
            # Group by disease type
            daily_by_disease = defaultdict(lambda: defaultdict(int))
            for row in qs:
                disease = get_disease_type(row['disease__name'])
                daily_by_disease[disease][row['appt_date']] += row['day_count']
            
            outbreaks = []
            
            # Analyze each disease
            for disease, daily_map in daily_by_disease.items():
                if len(daily_map) < min_days:
                    continue
                
                # Sort dates chronologically
                sorted_dates = sorted(daily_map.keys())
                
                # Look for consecutive growth periods
                i = 0
                while i < len(sorted_dates) - min_days + 1:
                    trend_start = i
                    trend_days = 1
                    first_count = daily_map[sorted_dates[i]]
                    
                    if first_count < min_cases:
                        i += 1
                        continue
                    
                    # Check for consecutive growth
                    last_count = first_count
                    for day_idx in range(i + 1, len(sorted_dates)):
                        current_count = daily_map[sorted_dates[day_idx]]
                        
                        if current_count > last_count:
                            trend_days += 1
                            last_count = current_count
                        else:
                            break
                    
                    # Check if meets outbreak criteria
                    if trend_days >= min_days:
                        growth_multiplier = last_count / first_count if first_count > 0 else 1.0
                        
                        if growth_multiplier >= growth_threshold:
                            severity = 'critical' if growth_multiplier >= 1.5 else 'warning'
                            
                            outbreaks.append({
                                'disease_name': disease,
                                'trend_days': trend_days,
                                'first_count': first_count,
                                'last_count': last_count,
                                'total_growth': round(growth_multiplier, 2),
                                'severity': severity,
                                'start_date': str(sorted_dates[trend_start]),
                                'end_date': str(sorted_dates[trend_start + trend_days - 1])
                            })
                            
                            self.logger.warning(
                                "Outbreak detected for %s: %sx growth over %d days",
                                disease, growth_multiplier, trend_days
                            )
                    
                    i = trend_start + 1
            
            return sorted(
                outbreaks,
                key=lambda x: (-x['total_growth'], -x['last_count'])
            )
            
        except Exception as e:
            self.logger.error(
                "Outbreak detection failed",
                exception=e
            )
            return []
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 6: Seasonal Pattern Detection
    # Learns and highlights disease trends based on seasons
    # ────────────────────────────────────────────────────────────────────────────
    
    def get_seasonal_patterns(
        self,
        disease_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict or List[Dict]:
        """
        FEATURE 6: Analyze seasonal patterns for disease.
        
        Returns disease occurrence by season (Summer, Monsoon, Winter).
        Helps predict seasonal outbreaks and plan interventions.
        
        For new users: Seasonal data helps identify when diseases are most
        common (e.g., malaria in monsoon). Use for resource planning.
        
        Args:
            disease_name: Specific disease (None = all diseases)
            start_date: Analysis period start
            end_date: Analysis period end
        
        Returns:
            If disease_name provided: Dictionary with seasonal breakdown
            If disease_name=None: List of all diseases with seasonal data
        
        Example:
            # Single disease analysis
            monsoon_flu = service.get_seasonal_patterns("Flu")
            print(f"Monsoon flu cases: {monsoon_flu['Monsoon']}")
            
            # All diseases
            all_patterns = service.get_seasonal_patterns()
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Get current month for seasonal mapping
            current_month = date.today().month
            
            if disease_name:
                # Single disease analysis
                qs = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        disease__name__icontains=disease_name,
                        disease__isnull=False
                    )
                    .select_related('disease')
                    .values('disease__season')
                    .annotate(case_count=Count('id'))
                )
                
                result = {
                    'disease_name': disease_name,
                    'Summer': 0,
                    'Monsoon': 0,
                    'Winter': 0,
                    'Unknown': 0
                }
                
                for row in qs:
                    season = row['disease__season'] or 'Unknown'
                    result[season] = row['case_count']
                
                total = sum(v for k, v in result.items() if k != 'disease_name')
                if total > 0:
                    for season in ['Summer', 'Monsoon', 'Winter', 'Unknown']:
                        if total > 0:
                            result[f'{season}_pct'] = round(
                                result.get(season, 0) / total * 100, 1
                            )
                
                peak_season = max(
                    ((s, c) for s, c in result.items() if s not in ['disease_name', 'Summer_pct', 'Monsoon_pct', 'Winter_pct', 'Unknown_pct']),
                    key=lambda x: x[1],
                    default=(None, 0)
                )[0]
                
                result['peak_season'] = peak_season
                
                self.logger.info(
                    "Seasonal pattern for %s: peak in %s",
                    disease_name, peak_season
                )
                
                return result
            
            else:
                # All diseases
                qs = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        disease__isnull=False
                    )
                    .select_related('disease')
                    .values('disease__name', 'disease__season')
                    .annotate(case_count=Count('id'))
                )
                
                disease_patterns = defaultdict(lambda: {
                    'Summer': 0, 'Monsoon': 0, 'Winter': 0, 'Unknown': 0
                })
                
                for row in qs:
                    disease = get_disease_type(row['disease__name'])
                    season = row['disease__season'] or 'Unknown'
                    disease_patterns[disease][season] += row['case_count']
                
                results = []
                for disease, patterns in disease_patterns.items():
                    total = sum(patterns.values())
                    results.append({
                        'disease_name': disease,
                        'seasonal_breakdown': patterns,
                        'peak_season': max(patterns, key=patterns.get),
                        'total_cases': total
                    })
                
                return sorted(results, key=lambda x: -x['total_cases'])
        
        except Exception as e:
            self.logger.error(
                "Seasonal pattern analysis failed",
                exception=e
            )
            return {} if disease_name else []
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 7: Doctor Performance Insights
    # Analyzes disease cases handled per doctor
    # ────────────────────────────────────────────────────────────────────────────
    
    def get_doctor_disease_insights(
        self,
        doctor_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict or List[Dict]:
        """
        FEATURE 7: Analyze doctor performance on disease cases.
        
        Returns disease case distribution per doctor.
        Helps evaluate workload, specialization, and expertise.
        
        For new users: Identifies which diseases each doctor handles most,
        useful for workload balancing and specialist identification.
        
        Args:
            doctor_id: Specific doctor (None = all doctors)
            start_date: Analysis period start
            end_date: Analysis period end
        
        Returns:
            If doctor_id: Doctor's disease case distribution
            If doctor_id=None: All doctors' insights
        
        Example:
            # Single doctor
            insights = service.get_doctor_disease_insights(doctor_id=5)
            print(f"Dr. {insights['doctor_name']} handled {insights['total_cases']} cases")
            
            # All doctors
            all_doctors = service.get_doctor_disease_insights()
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            if doctor_id:
                # Single doctor analysis
                doctor = Doctor.objects.filter(id=doctor_id).first()
                if not doctor:
                    self.logger.warning("Doctor not found: %s", doctor_id)
                    return {'error': 'Doctor not found'}
                
                qs = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        doctor_id=doctor_id,
                        disease__isnull=False
                    )
                    .select_related('disease')
                    .values('disease__name', 'disease__category')
                    .annotate(case_count=Count('id'))
                    .order_by('-case_count')
                )
                
                diseases = {}
                total_cases = 0
                
                for row in qs:
                    disease = get_disease_type(row['disease__name'])
                    count = row['case_count']
                    diseases[disease] = count
                    total_cases += count
                
                # Calculate case percentages
                for disease in diseases:
                    diseases[disease] = {
                        'cases': diseases[disease],
                        'percentage': round(diseases[disease] / total_cases * 100, 1) if total_cases > 0 else 0
                    }
                
                result = {
                    'doctor_id': doctor_id,
                    'doctor_name': f"{doctor.first_name} {doctor.last_name or ''}".strip(),
                    'clinic_name': doctor.clinic.clinic_name,
                    'total_cases': total_cases,
                    'unique_diseases': len(diseases),
                    'diseases': diseases,
                    'top_disease': max(diseases.items(), key=lambda x: x[1]['cases'], default=(None, {}))[0],
                    'period': f'{start_date} to {end_date}'
                }
                
                self.logger.info(
                    "Doctor insights for %s: %d cases",
                    doctor.first_name, total_cases
                )
                
                return result
            
            else:
                # All doctors analysis
                qs = (
                    Appointment.objects
                    .filter(
                        appointment_datetime__date__range=(start_date, end_date),
                        doctor__isnull=False,
                        disease__isnull=False
                    )
                    .select_related('doctor', 'disease')
                    .values(
                        'doctor_id',
                        'doctor__first_name',
                        'doctor__last_name',
                        'doctor__clinic__clinic_name',
                        'disease__name'
                    )
                    .annotate(case_count=Count('id'))
                )
                
                doctor_stats = defaultdict(lambda: {
                    'total_cases': 0,
                    'diseases': defaultdict(int)
                })
                
                doctor_info = {}
                
                for row in qs:
                    doc_id = row['doctor_id']
                    disease = get_disease_type(row['disease__name'])
                    count = row['case_count']
                    
                    doctor_stats[doc_id]['total_cases'] += count
                    doctor_stats[doc_id]['diseases'][disease] += count
                    
                    doctor_info[doc_id] = {
                        'name': f"{row['doctor__first_name']} {row['doctor__last_name'] or ''}".strip(),
                        'clinic': row['doctor__clinic__clinic_name']
                    }
                
                results = []
                for doc_id, stats in doctor_stats.items():
                    results.append({
                        'doctor_id': doc_id,
                        'doctor_name': doctor_info[doc_id]['name'],
                        'clinic_name': doctor_info[doc_id]['clinic'],
                        'total_cases': stats['total_cases'],
                        'unique_diseases': len(stats['diseases']),
                        'top_disease': max(
                            stats['diseases'].items(),
                            key=lambda x: x[1],
                            default=(None, 0)
                        )[0]
                    })
                
                return sorted(results, key=lambda x: -x['total_cases'])
        
        except Exception as e:
            self.logger.error(
                "Doctor insights generation failed",
                exception=e
            )
            return {'error': str(e)} if doctor_id else []
    
    def get_all_disease_trends(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_forecasts: bool = False
    ) -> List[Dict]:
        """
        Get trends for all diseases in a period.
        
        For new users: Comprehensive overview of all disease trends,
        optionally with forecasts for next 7 days.
        
        Args:
            start_date: Period start
            end_date: Period end
            include_forecasts: Whether to include 7-day forecasts
        
        Returns:
            List of disease trend dictionaries
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            current_month = date.today().month
            mid = (start_date + (end_date - start_date) // 2)
            
            # Get disease counts
            qs = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__isnull=False
                )
                .select_related('disease')
                .values('disease__name', 'disease__season')
                .annotate(case_count=Count('id'))
            )
            
            results = []
            for row in qs:
                disease = get_disease_type(row['disease__name'])
                season = row['disease__season']
                count = row['case_count']
                sw = get_seasonal_weight(season, current_month)
                
                result = {
                    'disease_name': disease,
                    'season': season,
                    'total_cases': count,
                    'seasonal_weight': sw,
                    'weighted_cases': round(count * sw, 2)
                }
                
                if include_forecasts:
                    # Would add forecast here
                    result['forecast_7_days'] = None
                
                results.append(result)
            
            return sorted(results, key=lambda x: -x['total_cases'])
        
        except Exception as e:
            self.logger.error(
                "Disease trends retrieval failed",
                exception=e
            )
            return []
