"""
Analytics Engine - Layer 2: Centralized Analytics Computations

This engine provides unified analytics capabilities:
- Time-series analysis and pattern recognition
- Statistical computations (mean, variance, trends)
- Disease surveillance and outbreak detection
- Medicine usage analytics
- Performance metrics and KPIs

For new users: This is the central hub for all data analysis.
It takes raw data from the aggregation layer and computes
meaningful metrics, trends, and patterns.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

from analytics.models import Appointment, Disease
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic, Doctor, Patient

from .aggregation import get_disease_type
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class AnalyticsEngine:
    """
    Central analytics engine for healthcare data analysis.
    
    This engine processes raw healthcare data to extract meaningful insights:
    - Disease trends and patterns
    - Medicine consumption analytics
    - Patient demographics analysis
    - Clinic performance metrics
    - Temporal pattern analysis
    
    Usage:
        engine = AnalyticsEngine()
        
        # Get disease analytics
        disease_stats = engine.analyze_disease_trends(days=30)
        
        # Get medicine usage patterns
        medicine_stats = engine.analyze_medicine_usage(days=90)
        
        # Get comprehensive health dashboard
        dashboard = engine.get_health_dashboard()
    """
    
    def __init__(self):
        """Initialize the analytics engine."""
        self.logger = logger
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DISEASE ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_disease_trends(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_demographics: bool = False
    ) -> Dict:
        """
        Analyze disease trends and patterns over time.
        
        For new users: This provides a comprehensive view of disease patterns,
        including which diseases are trending up/down, seasonal patterns,
        and demographic breakdowns.
        
        Args:
            start_date: Analysis period start
            end_date: Analysis period end
            include_demographics: Include age/gender breakdowns
            
        Returns:
            Dictionary containing:
                - disease_summary: Overall disease statistics
                - trends: Directional trends for each disease
                - seasonal_patterns: Seasonal occurrence patterns
                - demographics: Age/gender breakdown (if requested)
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Get disease counts with metadata
            disease_qs = (
                Appointment.objects
                .filter(
                    appointment_datetime__date__range=(start_date, end_date),
                    disease__isnull=False
                )
                .select_related('disease')
                .values('disease__name', 'disease__season', 'disease__category', 
                       'disease__severity')
                .annotate(
                    total_cases=Count('id'),
                    unique_patients=Count('patient_id', distinct=True),
                    unique_clinics=Count('clinic_id', distinct=True)
                )
                .order_by('-total_cases')
            )
            
            disease_summary = []
            total_cases = 0
            
            for row in disease_qs:
                dtype = get_disease_type(row['disease__name'])
                disease_summary.append({
                    'disease_name': dtype,
                    'category': row['disease__category'] or 'General',
                    'season': row['disease__season'],
                    'severity': row['disease__severity'],
                    'total_cases': row['total_cases'],
                    'unique_patients': row['unique_patients'],
                    'unique_clinics': row['unique_clinics'],
                    'avg_cases_per_clinic': round(
                        row['total_cases'] / max(row['unique_clinics'], 1), 2
                    )
                })
                total_cases += row['total_cases']
            
            # Calculate percentages
            for disease in disease_summary:
                disease['percentage'] = round(
                    (disease['total_cases'] / total_cases * 100) if total_cases > 0 else 0, 2
                )
            
            # Analyze trends (compare with previous period)
            period_days = (end_date - start_date).days
            prev_start = start_date - timedelta(days=period_days)
            prev_end = start_date - timedelta(days=1)
            
            trends = self._calculate_disease_trends(
                disease_summary, prev_start, prev_end, start_date, end_date
            )
            
            # Seasonal patterns
            seasonal_patterns = self._analyze_seasonal_patterns(start_date, end_date)
            
            result = {
                'period': f'{start_date} to {end_date}',
                'total_cases': total_cases,
                'total_diseases': len(disease_summary),
                'disease_summary': disease_summary[:20],  # Top 20
                'trends': trends,
                'seasonal_patterns': seasonal_patterns,
            }
            
            # Add demographics if requested
            if include_demographics:
                result['demographics'] = self._analyze_disease_demographics(
                    start_date, end_date
                )
            
            self.logger.info(
                "Disease trend analysis completed: %d diseases, %d total cases",
                len(disease_summary), total_cases
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Disease trend analysis failed: %s", str(e))
            return {
                'error': str(e),
                'disease_summary': [],
                'trends': [],
                'seasonal_patterns': {}
            }
    
    def _calculate_disease_trends(
        self,
        current_diseases: List[Dict],
        prev_start: date,
        prev_end: date,
        curr_start: date,
        curr_end: date
    ) -> List[Dict]:
        """Calculate trend direction for each disease."""
        
        # Get previous period data
        prev_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(prev_start, prev_end),
                disease__isnull=False
            )
            .select_related('disease')
            .values('disease__name')
            .annotate(prev_cases=Count('id'))
        )
        
        prev_map = {}
        for row in prev_qs:
            dtype = get_disease_type(row['disease__name'])
            prev_map[dtype] = row['prev_cases']
        
        trends = []
        for disease in current_diseases:
            dtype = disease['disease_name']
            current_cases = disease['total_cases']
            prev_cases = prev_map.get(dtype, 0)
            
            if prev_cases == 0:
                change_pct = 100.0 if current_cases > 0 else 0.0
                direction = 'new' if current_cases > 0 else 'stable'
            else:
                change_pct = round(((current_cases - prev_cases) / prev_cases) * 100, 2)
                direction = 'up' if change_pct > 10 else 'down' if change_pct < -10 else 'stable'
            
            trends.append({
                'disease_name': dtype,
                'current_cases': current_cases,
                'previous_cases': prev_cases,
                'change': current_cases - prev_cases,
                'change_percentage': change_pct,
                'direction': direction,
                'trend_strength': 'strong' if abs(change_pct) > 50 else 'moderate' if abs(change_pct) > 20 else 'weak'
            })
        
        # Sort by absolute change percentage
        trends.sort(key=lambda x: abs(x['change_percentage']), reverse=True)
        
        return trends
    
    def _analyze_seasonal_patterns(self, start_date: date, end_date: date) -> Dict:
        """Analyze disease patterns by season."""
        
        seasonal_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start_date, end_date),
                disease__isnull=False
            )
            .select_related('disease')
            .values('disease__name', 'disease__season')
            .annotate(case_count=Count('id'))
            .order_by('disease__season', '-case_count')
        )
        
        seasons = defaultdict(list)
        for row in seasonal_qs:
            dtype = get_disease_type(row['disease__name'])
            seasons[row['disease__season']].append({
                'disease_name': dtype,
                'case_count': row['case_count']
            })
        
        result = {}
        for season, diseases in seasons.items():
            # Aggregate by disease type
            disease_totals = defaultdict(int)
            for d in diseases:
                disease_totals[d['disease_name']] += d['case_count']
            
            sorted_diseases = sorted(
                disease_totals.items(), key=lambda x: -x[1]
            )
            
            result[season] = {
                'top_disease': sorted_diseases[0][0] if sorted_diseases else None,
                'top_disease_cases': sorted_diseases[0][1] if sorted_diseases else 0,
                'total_cases': sum(disease_totals.values()),
                'diseases': [
                    {'disease_name': d, 'case_count': c}
                    for d, c in sorted_diseases[:10]
                ]
            }
        
        return result
    
    def _analyze_disease_demographics(self, start_date: date, end_date: date) -> Dict:
        """Analyze disease patterns by demographics."""
        
        # Age group analysis
        today = date.today()
        demo_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start_date, end_date),
                disease__isnull=False,
                patient__dob__isnull=False
            )
            .select_related('disease', 'patient')
            .values('disease__name', 'patient__gender')
            .annotate(
                case_count=Count('id'),
                avg_age=Avg(
                    # Calculate age from DOB
                    case=(
                        Q(patient__dob__year__isnull=False)
                    ),
                    then=(today.year - 'patient__dob__year') - 
                         Q(patient__dob__month__gt=today.month) -
                         Q(patient__dob__month=today.month, patient__dob__day__gt=today.day)
                )
            )
            .order_by('-case_count')
        )
        
        # Simplified demographic analysis
        gender_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start_date, end_date),
                disease__isnull=False
            )
            .select_related('patient')
            .values('patient__gender', 'disease__name')
            .annotate(case_count=Count('id'))
        )
        
        gender_distribution = defaultdict(lambda: defaultdict(int))
        for row in gender_qs:
            dtype = get_disease_type(row['disease__name'])
            gender_distribution[row['patient__gender']][dtype] += row['case_count']
        
        return {
            'gender_distribution': dict(gender_distribution),
            'analysis_period': f'{start_date} to {end_date}'
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEDICINE ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_medicine_usage(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_trends: bool = True
    ) -> Dict:
        """
        Analyze medicine usage patterns and consumption.
        
        For new users: This shows which medicines are most used,
        how usage correlates with diseases, and consumption trends
        over time.
        
        Args:
            start_date: Analysis period start
            end_date: Analysis period end
            include_trends: Include usage trend analysis
            
        Returns:
            Dictionary containing:
                - medicine_summary: Overall medicine statistics
                - disease_medicine_map: Which medicines for which diseases
                - consumption_trends: Usage patterns over time
                - stock_correlation: Usage vs current stock levels
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Get medicine usage by disease
            usage_qs = (
                PrescriptionLine.objects
                .filter(
                    prescription_date__range=(start_date, end_date),
                    drug__isnull=False,
                    disease__isnull=False
                )
                .select_related('drug', 'disease')
                .values(
                    'drug__drug_name', 'drug__generic_name', 'drug__drug_strength',
                    'drug__dosage_type', 'disease__name', 'disease__season'
                )
                .annotate(
                    total_quantity=Sum('quantity'),
                    prescription_count=Count('id'),
                    avg_quantity=Avg('quantity')
                )
                .order_by('-total_quantity')
            )
            
            # Aggregate by medicine
            medicine_stats = defaultdict(lambda: {
                'total_quantity': 0,
                'prescription_count': 0,
                'diseases': defaultdict(int),
                'generic_name': '',
                'strength': '',
                'dosage_type': ''
            })
            
            for row in usage_qs:
                drug_name = row['drug__drug_name']
                dtype = get_disease_type(row['disease__name'])
                
                medicine_stats[drug_name]['total_quantity'] += row['total_quantity'] or 0
                medicine_stats[drug_name]['prescription_count'] += row['prescription_count'] or 0
                medicine_stats[drug_name]['diseases'][dtype] += row['total_quantity'] or 0
                medicine_stats[drug_name]['generic_name'] = row['drug__generic_name'] or ''
                medicine_stats[drug_name]['strength'] = row['drug__drug_strength']
                medicine_stats[drug_name]['dosage_type'] = row['drug__dosage_type']
            
            # Format results
            medicine_summary = []
            for drug_name, stats in medicine_stats.items():
                # Calculate percentage breakdown by disease
                total_qty = stats['total_quantity']
                disease_breakdown = [
                    {
                        'disease_name': dtype,
                        'quantity': qty,
                        'percentage': round((qty / total_qty * 100) if total_qty > 0 else 0, 2)
                    }
                    for dtype, qty in sorted(
                        stats['diseases'].items(), key=lambda x: -x[1]
                    )[:5]  # Top 5 diseases per medicine
                ]
                
                medicine_summary.append({
                    'drug_name': drug_name,
                    'generic_name': stats['generic_name'],
                    'strength': stats['strength'],
                    'dosage_type': stats['dosage_type'],
                    'total_quantity': total_qty,
                    'prescription_count': stats['prescription_count'],
                    'avg_quantity_per_rx': round(
                        total_qty / stats['prescription_count'], 2
                    ) if stats['prescription_count'] > 0 else 0,
                    'disease_breakdown': disease_breakdown
                })
            
            # Sort by total quantity
            medicine_summary.sort(key=lambda x: -x['total_quantity'])
            
            # Get current stock levels for correlation
            stock_map = {}
            for drug in DrugMaster.objects.values('drug_name', 'current_stock'):
                stock_map[drug['drug_name']] = drug['current_stock']
            
            # Add stock correlation
            for med in medicine_summary:
                med['current_stock'] = stock_map.get(med['drug_name'], 0)
                med['days_of_stock'] = round(
                    med['current_stock'] / (med['total_quantity'] / 
                    max((end_date - start_date).days, 1)), 1
                ) if med['total_quantity'] > 0 else 999
            
            result = {
                'period': f'{start_date} to {end_date}',
                'total_medicines': len(medicine_summary),
                'medicine_summary': medicine_summary[:30],  # Top 30
                'stock_correlation': {
                    'low_stock_medicines': [
                        med for med in medicine_summary 
                        if med['days_of_stock'] < 30
                    ][:10]
                }
            }
            
            # Add trends if requested
            if include_trends:
                result['consumption_trends'] = self._analyze_medicine_trends(
                    start_date, end_date
                )
            
            self.logger.info(
                "Medicine usage analysis completed: %d medicines analyzed",
                len(medicine_summary)
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Medicine usage analysis failed: %s", str(e))
            return {
                'error': str(e),
                'medicine_summary': [],
                'stock_correlation': {}
            }
    
    def _analyze_medicine_trends(self, start_date: date, end_date: date) -> List[Dict]:
        """Analyze medicine consumption trends over time."""
        
        # Get daily usage for top medicines
        top_meds_qs = (
            PrescriptionLine.objects
            .filter(prescription_date__range=(start_date, end_date))
            .values('drug__drug_name')
            .annotate(total_qty=Sum('quantity'))
            .order_by('-total_qty')[:10]
        )
        
        top_drug_names = [row['drug__drug_name'] for row in top_meds_qs]
        
        # Get daily time series for these medicines
        daily_qs = (
            PrescriptionLine.objects
            .filter(
                prescription_date__range=(start_date, end_date),
                drug__drug_name__in=top_drug_names
            )
            .annotate(rx_date=TruncDate('prescription_date'))
            .values('rx_date', 'drug__drug_name')
            .annotate(daily_qty=Sum('quantity'))
            .order_by('rx_date')
        )
        
        # Build time series
        trends = defaultdict(list)
        for row in daily_qs:
            trends[row['drug__drug_name']].append({
                'date': str(row['rx_date']),
                'quantity': row['daily_qty'] or 0
            })
        
        return [
            {
                'drug_name': drug_name,
                'daily_usage': usage_data,
                'avg_daily': round(
                    sum(d['quantity'] for d in usage_data) / len(usage_data), 2
                ) if usage_data else 0,
                'peak_usage': max(d['quantity'] for d in usage_data) if usage_data else 0
            }
            for drug_name, usage_data in trends.items()
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_health_dashboard(self, days: int = 30) -> Dict:
        """
        Get comprehensive health system dashboard.
        
        For new users: This provides a single API call to get all key
        metrics about the healthcare system - disease trends, medicine
        usage, clinic performance, and alerts.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Comprehensive dashboard with all key metrics
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Parallel analytics
        disease_analytics = self.analyze_disease_trends(start_date, end_date)
        medicine_analytics = self.analyze_medicine_usage(start_date, end_date)
        
        # Get system-wide metrics
        total_appointments = Appointment.objects.filter(
            appointment_datetime__date__range=(start_date, end_date)
        ).count()
        
        total_patients = Patient.objects.filter(
            clinic__isnull=False
        ).count()
        
        total_clinics = Clinic.objects.count()
        
        # Get stock alerts
        critical_stock = DrugMaster.objects.filter(current_stock__lte=10).count()
        out_of_stock = DrugMaster.objects.filter(current_stock=0).count()
        
        return {
            'period': f'{start_date} to {end_date}',
            'generated_at': date.today().isoformat(),
            'system_metrics': {
                'total_appointments': total_appointments,
                'total_patients': total_patients,
                'total_clinics': total_clinics,
                'avg_appointments_per_day': round(total_appointments / max(days, 1), 1)
            },
            'disease_surveillance': {
                'total_diseases': disease_analytics.get('total_diseases', 0),
                'total_cases': disease_analytics.get('total_cases', 0),
                'top_diseases': disease_analytics.get('disease_summary', [])[:5],
                'trending_up': [
                    t for t in disease_analytics.get('trends', [])
                    if t.get('direction') == 'up'
                ][:5]
            },
            'medicine_inventory': {
                'total_medicines': medicine_analytics.get('total_medicines', 0),
                'top_medicines': medicine_analytics.get('medicine_summary', [])[:5],
                'stock_alerts': {
                    'critical_stock_count': critical_stock,
                    'out_of_stock_count': out_of_stock,
                    'low_stock_medicines': medicine_analytics.get(
                        'stock_correlation', {}
                    ).get('low_stock_medicines', [])[:5]
                }
            },
            'alerts': {
                'disease_spikes': len([
                    t for t in disease_analytics.get('trends', [])
                    if t.get('trend_strength') == 'strong' and t.get('direction') == 'up'
                ]),
                'stock_critical': critical_stock + out_of_stock
            }
        }