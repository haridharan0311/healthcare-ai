"""
Decision Engine - Layer 4: Business Rule Evaluation & Decision Making

This engine provides decision-making capabilities:
- Automated alert generation
- Restock recommendations with priority scoring
- Resource allocation decisions
- Risk assessment and mitigation
- Action prioritization

For new users: This engine takes predictions and analytics to make
actionable recommendations, helping healthcare managers make informed
decisions about resource allocation, inventory management, and
emergency response.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate

from analytics.models import Appointment, Disease
from inventory.models import DrugMaster, PrescriptionLine
from core.models import Clinic, Doctor, Patient

from .analytics_engine import AnalyticsEngine
from .prediction_engine import PredictionEngine
from .aggregation import get_disease_type
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class DecisionEngine:
    """
    Decision engine for healthcare management.
    
    This engine converts analytics and predictions into actionable decisions:
    - Inventory restock decisions
    - Disease outbreak response decisions
    - Resource allocation decisions
    - Risk mitigation decisions
    - Priority-based action items
    
    Usage:
        engine = DecisionEngine()
        
        # Get all decisions
        decisions = engine.generate_decisions()
        
        # Get restock decisions
        restock_decisions = engine.make_restock_decisions()
        
        # Get outbreak response decisions
        outbreak_decisions = engine.make_outbreak_response_decisions()
    """
    
    def __init__(self):
        """Initialize the decision engine."""
        self.logger = logger
        self.analytics_engine = AnalyticsEngine()
        self.prediction_engine = PredictionEngine()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPREHENSIVE DECISION GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_decisions(self, days_ahead: int = 14) -> Dict:
        """
        Generate comprehensive set of decisions for healthcare management.
        
        For new users: This is the main entry point for getting all
        recommended actions. It analyzes the current situation and
        generates prioritized decisions across all areas.
        
        Args:
            days_ahead: Forecast horizon for decisions
            
        Returns:
            Dictionary containing all decision categories with priorities
        """
        # Get analytics and predictions
        analytics = self.analytics_engine.get_health_dashboard(days=30)
        predictions = self.prediction_engine.get_forecast_dashboard(days_ahead=days_ahead)
        
        # Generate decisions for each category
        restock_decisions = self.make_restock_decisions()
        outbreak_decisions = self.make_outbreak_response_decisions()
        resource_decisions = self.make_resource_allocation_decisions()
        risk_decisions = self.make_risk_mitigation_decisions()
        
        # Calculate overall priority score
        total_critical = (
            len([d for d in restock_decisions if d['priority'] == 'critical']) +
            len([d for d in outbreak_decisions if d['priority'] == 'critical']) +
            len([d for d in resource_decisions if d['priority'] == 'critical']) +
            len([d for d in risk_decisions if d['priority'] == 'critical'])
        )
        
        total_high = (
            len([d for d in restock_decisions if d['priority'] == 'high']) +
            len([d for d in outbreak_decisions if d['priority'] == 'high']) +
            len([d for d in resource_decisions if d['priority'] == 'high']) +
            len([d for d in risk_decisions if d['priority'] == 'high'])
        )
        
        return {
            'generated_at': date.today().isoformat(),
            'forecast_horizon': f"Next {days_ahead} days",
            'summary': {
                'total_decisions': len(restock_decisions) + len(outbreak_decisions) + 
                                 len(resource_decisions) + len(risk_decisions),
                'critical_decisions': total_critical,
                'high_priority_decisions': total_high,
                'system_risk_level': self._calculate_system_risk_level(
                    total_critical, total_high
                )
            },
            'decisions': {
                'restock': restock_decisions,
                'outbreak_response': outbreak_decisions,
                'resource_allocation': resource_decisions,
                'risk_mitigation': risk_decisions
            },
            'action_items': self._generate_action_items(
                restock_decisions, outbreak_decisions, 
                resource_decisions, risk_decisions
            )
        }
    
    def _calculate_system_risk_level(self, critical: int, high: int) -> str:
        """Calculate overall system risk level."""
        if critical >= 5:
            return "CRITICAL"
        elif critical >= 2 or high >= 5:
            return "HIGH"
        elif critical >= 1 or high >= 3:
            return "ELEVATED"
        elif high >= 1:
            return "GUARDED"
        else:
            return "LOW"
    
    def _generate_action_items(self, *decision_lists) -> List[Dict]:
        """Generate prioritized action items from all decisions."""
        action_items = []
        
        for decisions in decision_lists:
            for decision in decisions:
                if decision['priority'] in ['critical', 'high']:
                    action_items.append({
                        'id': f"{decision['category']}-{hash(str(decision)) % 10000}",
                        'title': decision['title'],
                        'description': decision['description'],
                        'priority': decision['priority'],
                        'category': decision['category'],
                        'deadline': decision.get('deadline', str(date.today() + timedelta(days=1))),
                        'assigned_to': decision.get('assigned_to', 'Healthcare Manager'),
                        'estimated_impact': decision.get('estimated_impact', 'Medium')
                    })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        action_items.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        return action_items[:20]  # Top 20 action items
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESTOCK DECISIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def make_restock_decisions(self, start_date: Optional[date] = None, 
                              end_date: Optional[date] = None) -> List[Dict]:
        """
        Generate restock decisions based on current stock and predicted demand.
        
        For new users: This analyzes current inventory levels against
        predicted medicine demand to recommend which medicines to order
        and in what quantities.
        
        Returns:
            List of restock decisions with priority and recommended quantities
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            # Get medicine demand predictions
            demand_forecast = self.prediction_engine.predict_medicine_demand(
                days_ahead=30,
                start_date=start_date,
                end_date=end_date
            )
            
            decisions = []
            
            for medicine in demand_forecast.get('demand_forecasts', []):
                current_stock = medicine['current_stock']
                predicted_demand = medicine['total_predicted_demand']
                days_of_stock = medicine['days_of_stock']
                
                # Calculate priority based on days of stock
                if days_of_stock <= 7:
                    priority = 'critical'
                    urgency = 'Immediate order required'
                    deadline = date.today() + timedelta(days=1)
                elif days_of_stock <= 14:
                    priority = 'high'
                    urgency = 'Order within 3 days'
                    deadline = date.today() + timedelta(days=3)
                elif days_of_stock <= 30:
                    priority = 'medium'
                    urgency = 'Order within 1 week'
                    deadline = date.today() + timedelta(days=7)
                else:
                    priority = 'low'
                    urgency = 'Monitor stock levels'
                    deadline = date.today() + timedelta(days=14)
                
                # Calculate recommended order quantity
                safety_stock = predicted_demand * 0.2  # 20% safety buffer
                recommended_quantity = max(
                    0, 
                    int(predicted_demand + safety_stock - current_stock)
                )
                
                if recommended_quantity > 0 or priority in ['critical', 'high']:
                    decisions.append({
                        'id': f"RESTOCK-{medicine['drug_name'][:3].upper()}-{hash(medicine['drug_name']) % 1000}",
                        'category': 'restock',
                        'drug_name': medicine['drug_name'],
                        'generic_name': medicine['generic_name'],
                        'strength': medicine['strength'],
                        'current_stock': current_stock,
                        'predicted_demand': predicted_demand,
                        'days_of_stock': days_of_stock,
                        'recommended_quantity': recommended_quantity,
                        'estimated_cost': round(recommended_quantity * 10, 2),  # Estimated cost
                        'priority': priority,
                        'urgency': urgency,
                        'deadline': str(deadline),
                        'title': f"Restock {medicine['drug_name']}",
                        'description': (
                            f"Current stock ({current_stock}) will last {days_of_stock:.1f} days. "
                            f"Predicted 30-day demand: {predicted_demand:.0f} units. "
                            f"Recommended order: {recommended_quantity} units."
                        ),
                        'assigned_to': 'Pharmacy Manager',
                        'estimated_impact': 'High' if priority in ['critical', 'high'] else 'Medium'
                    })
            
            # Sort by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            decisions.sort(key=lambda x: (priority_order.get(x['priority'], 4), -x['recommended_quantity']))
            
            return decisions
            
        except Exception as e:
            self.logger.error("Restock decision generation failed: %s", str(e))
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OUTBREAK RESPONSE DECISIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def make_outbreak_response_decisions(self, start_date: Optional[date] = None,
                                        end_date: Optional[date] = None) -> List[Dict]:
        """
        Generate outbreak response decisions.
        
        For new users: This analyzes disease patterns and predictions
        to recommend specific actions for disease outbreak prevention
        and control.
        
        Returns:
            List of outbreak response decisions with specific actions
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range(days_back=60)
            
            # Get outbreak predictions
            outbreak_forecast = self.prediction_engine.predict_disease_outbreaks(
                days_ahead=14,
                start_date=start_date,
                end_date=end_date
            )
            
            decisions = []
            
            for alert in outbreak_forecast.get('outbreak_alerts', []):
                disease_name = alert['disease_name']
                severity = alert['severity']
                predicted_increase = alert['predicted_increase']
                confidence = alert['confidence']
                
                # Determine priority based on severity and confidence
                if severity >= 4 or (severity >= 3 and confidence >= 0.8):
                    priority = 'critical'
                    response_level = 'Emergency Response'
                    deadline = date.today()
                elif severity >= 3 or (severity >= 2 and confidence >= 0.8):
                    priority = 'high'
                    response_level = 'Enhanced Surveillance'
                    deadline = date.today() + timedelta(days=1)
                elif severity >= 2:
                    priority = 'medium'
                    response_level = 'Increased Monitoring'
                    deadline = date.today() + timedelta(days=3)
                else:
                    priority = 'low'
                    response_level = 'Routine Monitoring'
                    deadline = date.today() + timedelta(days=7)
                
                # Generate specific response actions
                actions = self._generate_outbreak_response_actions(
                    disease_name, severity, predicted_increase
                )
                
                decisions.append({
                    'id': f"OUTBREAK-{disease_name[:3].upper()}-{hash(disease_name) % 1000}",
                    'category': 'outbreak_response',
                    'disease_name': disease_name,
                    'severity': severity,
                    'predicted_increase': predicted_increase,
                    'confidence': confidence,
                    'response_level': response_level,
                    'priority': priority,
                    'deadline': str(deadline),
                    'title': f"Respond to {disease_name} outbreak",
                    'description': (
                        f"Predicted {predicted_increase:.0f}% increase in {disease_name} cases. "
                        f"Confidence: {confidence:.0%}. Severity level: {severity}/5. "
                        f"Response level: {response_level}."
                    ),
                    'recommended_actions': actions,
                    'assigned_to': 'Public Health Officer',
                    'estimated_impact': 'Critical' if priority == 'critical' else 'High'
                })
            
            # Sort by severity and confidence
            decisions.sort(key=lambda x: (-x['severity'], -x['confidence']))
            
            return decisions
            
        except Exception as e:
            self.logger.error("Outbreak response decision generation failed: %s", str(e))
            return []
    
    def _generate_outbreak_response_actions(self, disease_name: str, 
                                           severity: int, increase_pct: float) -> List[str]:
        """Generate specific response actions based on disease and severity."""
        actions = []
        
        # Common actions for all outbreaks
        if severity >= 2:
            actions.append("Increase disease surveillance and reporting")
            actions.append("Review and update treatment protocols")
        
        if severity >= 3:
            actions.append("Alert healthcare facilities and staff")
            actions.append("Prepare isolation facilities if needed")
            actions.append("Stockpile essential medicines and supplies")
        
        if severity >= 4:
            actions.append("Activate emergency response team")
            actions.append("Implement community awareness campaigns")
            actions.append("Coordinate with regional health authorities")
            actions.append("Consider movement restrictions if recommended")
        
        # Disease-specific actions
        disease_specific = {
            'flu': ["Distribute masks and hand sanitizer", "Set up fever clinics"],
            'diarrhea': ["Ensure clean water supply", "Monitor food safety"],
            'respiratory': ["Increase ventilation in facilities", "Promote respiratory hygiene"],
            'vector': ["Implement vector control measures", "Eliminate breeding sites"]
        }
        
        disease_lower = disease_name.lower()
        for key, specific_actions in disease_specific.items():
            if key in disease_lower:
                actions.extend(specific_actions)
                break
        
        return actions
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESOURCE ALLOCATION DECISIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def make_resource_allocation_decisions(self, start_date: Optional[date] = None,
                                          end_date: Optional[date] = None) -> List[Dict]:
        """
        Generate resource allocation decisions.
        
        For new users: This analyzes predicted patient volumes and
        resource needs to recommend optimal allocation of staff,
        equipment, and facilities.
        
        Returns:
            List of resource allocation decisions
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range(days_back=60)
            
            # Get clinic resource predictions
            resource_forecast = self.prediction_engine.predict_clinic_resource_needs(
                days_ahead=14,
                start_date=start_date,
                end_date=end_date
            )
            
            decisions = []
            
            for clinic in resource_forecast.get('clinic_forecasts', []):
                clinic_name = clinic['clinic_name']
                predicted_patients = clinic['predicted_daily_patients']
                current_avg = clinic['current_avg_daily_patients']
                trend = clinic['trend_direction']
                
                # Calculate resource needs
                staff_needed = clinic['resource_recommendations']['staff_needed']
                rooms_needed = clinic['resource_recommendations']['consultation_rooms']
                
                # Determine if resource increase is needed
                if predicted_patients > current_avg * 1.5:
                    priority = 'high'
                    action = 'Increase resources significantly'
                elif predicted_patients > current_avg * 1.2:
                    priority = 'medium'
                    action = 'Moderate resource increase'
                elif trend == 'up':
                    priority = 'low'
                    action = 'Monitor and prepare'
                else:
                    priority = 'low'
                    action = 'Maintain current levels'
                
                if priority in ['high', 'medium'] or trend == 'up':
                    decisions.append({
                        'id': f"RESOURCE-{clinic_name[:3].upper()}-{hash(clinic_name) % 1000}",
                        'category': 'resource_allocation',
                        'clinic_name': clinic_name,
                        'predicted_daily_patients': predicted_patients,
                        'current_avg_patients': current_avg,
                        'trend': trend,
                        'priority': priority,
                        'deadline': str(date.today() + timedelta(days=3)),
                        'title': f"Allocate resources for {clinic_name}",
                        'description': (
                            f"Predicted {predicted_patients:.0f} patients/day "
                            f"(current avg: {current_avg:.0f}). Trend: {trend}. "
                            f"Action: {action}."
                        ),
                        'recommended_actions': [
                            f"Deploy {staff_needed} staff members",
                            f"Prepare {rooms_needed} consultation rooms",
                            f"Ensure adequate medicine stock for {predicted_patients * 14:.0f} patients"
                        ],
                        'assigned_to': 'Clinic Manager',
                        'estimated_impact': 'High' if priority == 'high' else 'Medium'
                    })
            
            # Sort by predicted patient volume
            decisions.sort(key=lambda x: -x['predicted_daily_patients'])
            
            return decisions
            
        except Exception as e:
            self.logger.error("Resource allocation decision generation failed: %s", str(e))
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RISK MITIGATION DECISIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def make_risk_mitigation_decisions(self, start_date: Optional[date] = None,
                                      end_date: Optional[date] = None) -> List[Dict]:
        """
        Generate risk mitigation decisions.
        
        For new users: This identifies potential risks in the healthcare
        system and recommends preventive actions to mitigate them before
        they become critical issues.
        
        Returns:
            List of risk mitigation decisions
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
            decisions = []
            
            # Check for stock-out risks
            stock_out_risks = self._identify_stock_out_risks()
            decisions.extend(stock_out_risks)
            
            # Check for disease surveillance gaps
            surveillance_gaps = self._identify_surveillance_gaps(start_date, end_date)
            decisions.extend(surveillance_gaps)
            
            # Check for resource constraints
            resource_constraints = self._identify_resource_constraints()
            decisions.extend(resource_constraints)
            
            # Check for quality of care issues
            quality_issues = self._identify_quality_issues(start_date, end_date)
            decisions.extend(quality_issues)
            
            # Sort by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            decisions.sort(key=lambda x: (priority_order.get(x['priority'], 4), x['title']))
            
            return decisions
            
        except Exception as e:
            self.logger.error("Risk mitigation decision generation failed: %s", str(e))
            return []
    
    def _identify_stock_out_risks(self) -> List[Dict]:
        """Identify potential stock-out risks."""
        decisions = []
        
        # Get drugs with critically low stock
        critical_drugs = DrugMaster.objects.filter(current_stock__lte=10)
        
        for drug in critical_drugs:
            # Check recent usage
            recent_usage = PrescriptionLine.objects.filter(
                drug=drug,
                prescription_date__gte=date.today() - timedelta(days=30)
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            daily_usage = recent_usage / 30 if recent_usage > 0 else 0
            
            if daily_usage > 0:
                days_until_stockout = drug.current_stock / daily_usage
                
                if days_until_stockout <= 3:
                    priority = 'critical'
                elif days_until_stockout <= 7:
                    priority = 'high'
                elif days_until_stockout <= 14:
                    priority = 'medium'
                else:
                    priority = 'low'
                
                decisions.append({
                    'id': f"RISK-STOCK-{drug.drug_name[:3].upper()}-{drug.id}",
                    'category': 'risk_mitigation',
                    'risk_type': 'stock_out',
                    'drug_name': drug.drug_name,
                    'current_stock': drug.current_stock,
                    'daily_usage': round(daily_usage, 2),
                    'days_until_stockout': round(days_until_stockout, 1),
                    'priority': priority,
                    'deadline': str(date.today() + timedelta(days=max(1, int(days_until_stockout) - 1))),
                    'title': f"Prevent stock-out of {drug.drug_name}",
                    'description': (
                        f"Current stock: {drug.current_stock} units. "
                        f"Daily usage: {daily_usage:.1f} units. "
                        f"Expected stock-out in {days_until_stockout:.1f} days."
                    ),
                    'recommended_actions': [
                        f"Order {int(daily_usage * 30)} units immediately",
                        "Identify alternative suppliers",
                        "Consider therapeutic alternatives"
                    ],
                    'assigned_to': 'Pharmacy Manager',
                    'estimated_impact': 'High'
                })
        
        return decisions
    
    def _identify_surveillance_gaps(self, start_date: date, end_date: date) -> List[Dict]:
        """Identify gaps in disease surveillance."""
        decisions = []
        
        # Check for diseases with sudden increases
        disease_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start_date - timedelta(days=14), end_date),
                disease__isnull=False
            )
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name')
            .annotate(daily_count=Count('id'))
        )
        
        # Build time series by disease
        disease_data = defaultdict(lambda: defaultdict(int))
        for row in disease_qs:
            dtype = get_disease_type(row['disease__name'])
            disease_data[dtype][row['appt_date']] = row['daily_count']
        
        # Check for surveillance gaps
        for dtype, daily_map in disease_data.items():
            sorted_dates = sorted(daily_map.keys())
            if len(sorted_dates) < 14:
                # Check for reporting gaps
                gaps = []
                for i in range(len(sorted_dates) - 1):
                    if (sorted_dates[i+1] - sorted_dates[i]).days > 2:
                        gaps.append(str(sorted_dates[i]))
                
                if gaps:
                    decisions.append({
                        'id': f"RISK-SURV-{dtype[:3].upper()}-{hash(dtype) % 1000}",
                        'category': 'risk_mitigation',
                        'risk_type': 'surveillance_gap',
                        'disease_name': dtype,
                        'priority': 'medium',
                        'deadline': str(date.today() + timedelta(days=7)),
                        'title': f"Address surveillance gaps for {dtype}",
                        'description': (
                            f"Missing surveillance data on {len(gaps)} occasions in the past 14 days. "
                            f"This may indicate reporting issues or data quality problems."
                        ),
                        'recommended_actions': [
                            "Review reporting procedures with healthcare facilities",
                            "Implement automated data collection if possible",
                            "Conduct data quality audit"
                        ],
                        'assigned_to': 'Surveillance Officer',
                        'estimated_impact': 'Medium'
                    })
        
        return decisions
    
    def _identify_resource_constraints(self) -> List[Dict]:
        """Identify resource constraints across clinics."""
        decisions = []
        
        # Check for clinics with high patient-to-staff ratios
        clinics = Clinic.objects.all()
        
        for clinic in clinics:
            # Count recent appointments
            recent_appointments = Appointment.objects.filter(
                clinic=clinic,
                appointment_datetime__date__gte=date.today() - timedelta(days=30)
            ).count()
            
            # Count doctors in clinic
            doctors = Doctor.objects.filter(clinic=clinic).count()
            
            if doctors > 0:
                patients_per_doctor = recent_appointments / doctors
                
                if patients_per_doctor > 100:
                    priority = 'high'
                elif patients_per_doctor > 50:
                    priority = 'medium'
                else:
                    priority = 'low'
                
                if priority in ['high', 'medium']:
                    decisions.append({
                        'id': f"RISK-RESOURCE-{clinic.clinic_name[:3].upper()}-{clinic.id}",
                        'category': 'risk_mitigation',
                        'risk_type': 'resource_constraint',
                        'clinic_name': clinic.clinic_name,
                        'patients_per_doctor': round(patients_per_doctor, 1),
                        'priority': priority,
                        'deadline': str(date.today() + timedelta(days=14)),
                        'title': f"Address resource constraints at {clinic.clinic_name}",
                        'description': (
                            f"Patient-to-doctor ratio: {patients_per_doctor:.1f}:1. "
                            f"This may lead to burnout and reduced quality of care."
                        ),
                        'recommended_actions': [
                            "Recruit additional healthcare workers",
                            "Optimize appointment scheduling",
                            "Consider task-shifting where appropriate"
                        ],
                        'assigned_to': 'HR Manager',
                        'estimated_impact': 'High'
                    })
        
        return decisions
    
    def _identify_quality_issues(self, start_date: date, end_date: date) -> List[Dict]:
        """Identify potential quality of care issues."""
        decisions = []
        
        # Check for clinics with high no-show rates
        clinics = Clinic.objects.all()
        
        for clinic in clinics:
            appointments = Appointment.objects.filter(
                clinic=clinic,
                appointment_datetime__date__range=(start_date, end_date)
            )
            
            total = appointments.count()
            if total > 0:
                no_shows = appointments.filter(
                    appointment_status__icontains='no show'
                ).count()
                
                no_show_rate = (no_shows / total) * 100
                
                if no_show_rate > 20:
                    priority = 'high'
                elif no_show_rate > 10:
                    priority = 'medium'
                else:
                    priority = 'low'
                
                if priority in ['high', 'medium']:
                    decisions.append({
                        'id': f"RISK-QUALITY-{clinic.clinic_name[:3].upper()}-{clinic.id}",
                        'category': 'risk_mitigation',
                        'risk_type': 'quality_issue',
                        'clinic_name': clinic.clinic_name,
                        'no_show_rate': round(no_show_rate, 1),
                        'priority': priority,
                        'deadline': str(date.today() + timedelta(days=7)),
                        'title': f"Address high no-show rate at {clinic.clinic_name}",
                        'description': (
                            f"No-show rate: {no_show_rate:.1f}% over {total} appointments. "
                            f"This indicates potential access or satisfaction issues."
                        ),
                        'recommended_actions': [
                            "Implement appointment reminder system",
                            "Review clinic hours and accessibility",
                            "Conduct patient satisfaction survey"
                        ],
                        'assigned_to': 'Clinic Manager',
                        'estimated_impact': 'Medium'
                    })
        
        return decisions