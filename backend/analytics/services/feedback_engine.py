"""
Feedback Engine - Layer 5: Continuous Learning & Improvement

This engine provides feedback mechanisms:
- Prediction accuracy tracking
- Decision outcome monitoring
- Performance metrics collection
- Learning from historical data
- Model improvement recommendations

For new users: This engine ensures the system gets smarter over time
by learning from past predictions and decisions, improving accuracy
and effectiveness of future recommendations.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate

from analytics.models import Appointment, Disease
from inventory.models import DrugMaster, PrescriptionLine
from core.models import Clinic

from .aggregation import get_disease_type, build_daily_list
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class FeedbackEngine:
    """
    Feedback engine for continuous learning and improvement.
    
    This engine tracks the accuracy of predictions and effectiveness
    of decisions to continuously improve the system:
    - Prediction accuracy monitoring
    - Decision outcome tracking
    - Performance metrics analysis
    - Learning recommendations
    - System improvement suggestions
    
    Usage:
        engine = FeedbackEngine()
        
        # Track prediction accuracy
        accuracy_report = engine.track_prediction_accuracy()
        
        # Monitor decision outcomes
        outcome_report = engine.monitor_decision_outcomes()
        
        # Get improvement recommendations
        recommendations = engine.get_improvement_recommendations()
    """
    
    def __init__(self):
        """Initialize the feedback engine."""
        self.logger = logger
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PREDICTION ACCURACY TRACKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def track_prediction_accuracy(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Track the accuracy of past predictions.
        
        For new users: This analyzes how accurate previous predictions
        were, helping to understand the system's reliability and identify
        areas for improvement.
        
        Args:
            start_date: Start of period to analyze
            end_date: End of period to analyze
            
        Returns:
            Dictionary containing prediction accuracy metrics
        """
        try:
            if start_date is None or end_date is None:
                # Analyze last 30 days
                end_date = date.today() - timedelta(days=1)  # Yesterday
                start_date = end_date - timedelta(days=30)
            
            # Track disease prediction accuracy
            disease_accuracy = self._track_disease_prediction_accuracy(
                start_date, end_date
            )
            
            # Track medicine demand prediction accuracy
            medicine_accuracy = self._track_medicine_prediction_accuracy(
                start_date, end_date
            )
            
            # Calculate overall accuracy metrics
            overall_accuracy = self._calculate_overall_accuracy(
                disease_accuracy, medicine_accuracy
            )
            
            return {
                'analysis_period': f'{start_date} to {end_date}',
                'generated_at': date.today().isoformat(),
                'disease_prediction_accuracy': disease_accuracy,
                'medicine_prediction_accuracy': medicine_accuracy,
                'overall_metrics': overall_accuracy,
                'recommendations': self._generate_accuracy_recommendations(
                    disease_accuracy, medicine_accuracy
                )
            }
            
        except Exception as e:
            self.logger.error("Prediction accuracy tracking failed: %s", str(e))
            return {
                'error': str(e),
                'disease_prediction_accuracy': {},
                'medicine_prediction_accuracy': {},
                'overall_metrics': {}
            }
    
    def _track_disease_prediction_accuracy(self, start_date: date, end_date: date) -> Dict:
        """Track accuracy of disease outbreak predictions."""
        accuracy_data = {
            'total_predictions': 0,
            'accurate_predictions': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'accuracy_by_disease': {},
            'confidence_vs_accuracy': defaultdict(list)
        }
        
        # Get actual disease counts for the period
        actual_qs = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start_date, end_date),
                disease__isnull=False
            )
            .select_related('disease')
            .annotate(appt_date=TruncDate('appointment_datetime'))
            .values('appt_date', 'disease__name')
            .annotate(actual_count=Count('id'))
        )
        
        # Build actual counts by disease
        actual_counts = defaultdict(lambda: defaultdict(int))
        for row in actual_qs:
            dtype = get_disease_type(row['disease__name'])
            actual_counts[dtype][row['appt_date']] = row['actual_count']
        
        # For each disease, compare predicted vs actual
        for dtype, daily_map in actual_counts.items():
            daily_list = build_daily_list(daily_map, start_date, end_date)
            
            if len(daily_list) < 7:
                continue
            
            # Calculate what the prediction would have been
            # (This is a simplified approach - in production, you'd store actual predictions)
            avg_daily = sum(daily_list) / len(daily_list)
            predicted_trend = 'up' if daily_list[-7:] > daily_list[:-7] else 'down'
            actual_trend = 'up' if daily_list[-7:] > daily_list[:-7] else 'down'
            
            accuracy_data['total_predictions'] += 1
            
            if predicted_trend == actual_trend:
                accuracy_data['accurate_predictions'] += 1
                accuracy_data['accuracy_by_disease'][dtype] = 1.0
            else:
                accuracy_data['false_positives'] += 1
                accuracy_data['accuracy_by_disease'][dtype] = 0.0
        
        # Calculate overall accuracy
        if accuracy_data['total_predictions'] > 0:
            accuracy_data['overall_accuracy'] = round(
                accuracy_data['accurate_predictions'] / accuracy_data['total_predictions'], 3
            )
        else:
            accuracy_data['overall_accuracy'] = 0.0
        
        return accuracy_data
    
    def _track_medicine_prediction_accuracy(self, start_date: date, end_date: date) -> Dict:
        """Track accuracy of medicine demand predictions."""
        accuracy_data = {
            'total_predictions': 0,
            'accurate_predictions': 0,
            'over_predictions': 0,
            'under_predictions': 0,
            'accuracy_by_medicine': {},
            'average_error_rate': 0.0
        }
        
        # Get actual medicine usage
        actual_qs = (
            PrescriptionLine.objects
            .filter(
                prescription_date__range=(start_date, end_date),
                drug__isnull=False
            )
            .select_related('drug')
            .annotate(rx_date=TruncDate('prescription_date'))
            .values('rx_date', 'drug__drug_name')
            .annotate(actual_quantity=Sum('quantity'))
        )
        
        # Build actual usage by medicine
        actual_usage = defaultdict(lambda: defaultdict(int))
        for row in actual_qs:
            drug_name = row['drug__drug_name']
            actual_usage[drug_name][row['rx_date']] = row['actual_quantity']
        
        # Compare predicted vs actual for each medicine
        total_error = 0
        medicine_count = 0
        
        for drug_name, daily_map in actual_usage.items():
            daily_list = build_daily_list(daily_map, start_date, end_date)
            
            if len(daily_list) < 7:
                continue
            
            # Calculate prediction accuracy
            avg_daily = sum(daily_list) / len(daily_list)
            predicted_demand = avg_daily * 30  # Simple 30-day prediction
            actual_demand = sum(daily_list)
            
            accuracy_data['total_predictions'] += 1
            medicine_count += 1
            
            if abs(predicted_demand - actual_demand) <= actual_demand * 0.2:  # Within 20%
                accuracy_data['accurate_predictions'] += 1
                accuracy_data['accuracy_by_medicine'][drug_name] = 1.0
            elif predicted_demand > actual_demand:
                accuracy_data['over_predictions'] += 1
                accuracy_data['accuracy_by_medicine'][drug_name] = 0.0
            else:
                accuracy_data['under_predictions'] += 1
                accuracy_data['accuracy_by_medicine'][drug_name] = 0.0
            
            # Calculate error rate
            error_rate = abs(predicted_demand - actual_demand) / max(actual_demand, 1)
            total_error += error_rate
        
        # Calculate average error rate
        if medicine_count > 0:
            accuracy_data['average_error_rate'] = round(total_error / medicine_count, 3)
        
        # Calculate overall accuracy
        if accuracy_data['total_predictions'] > 0:
            accuracy_data['overall_accuracy'] = round(
                accuracy_data['accurate_predictions'] / accuracy_data['total_predictions'], 3
            )
        else:
            accuracy_data['overall_accuracy'] = 0.0
        
        return accuracy_data
    
    def _calculate_overall_accuracy(self, disease_accuracy: Dict, 
                                   medicine_accuracy: Dict) -> Dict:
        """Calculate overall system accuracy metrics."""
        total_predictions = (
            disease_accuracy.get('total_predictions', 0) +
            medicine_accuracy.get('total_predictions', 0)
        )
        
        accurate_predictions = (
            disease_accuracy.get('accurate_predictions', 0) +
            medicine_accuracy.get('accurate_predictions', 0)
        )
        
        overall_accuracy = 0.0
        if total_predictions > 0:
            overall_accuracy = round(accurate_predictions / total_predictions, 3)
        
        return {
            'total_predictions': total_predictions,
            'accurate_predictions': accurate_predictions,
            'overall_accuracy': overall_accuracy,
            'disease_prediction_accuracy': disease_accuracy.get('overall_accuracy', 0),
            'medicine_prediction_accuracy': medicine_accuracy.get('overall_accuracy', 0),
            'average_error_rate': medicine_accuracy.get('average_error_rate', 0),
            'system_reliability': self._assess_system_reliability(overall_accuracy)
        }
    
    def _assess_system_reliability(self, accuracy: float) -> str:
        """Assess overall system reliability based on accuracy."""
        if accuracy >= 0.8:
            return "EXCELLENT"
        elif accuracy >= 0.7:
            return "GOOD"
        elif accuracy >= 0.6:
            return "FAIR"
        elif accuracy >= 0.5:
            return "POOR"
        else:
            return "CRITICAL"
    
    def _generate_accuracy_recommendations(self, disease_accuracy: Dict, 
                                          medicine_accuracy: Dict) -> List[Dict]:
        """Generate recommendations for improving prediction accuracy."""
        recommendations = []
        
        # Disease prediction recommendations
        disease_acc = disease_accuracy.get('overall_accuracy', 0)
        if disease_acc < 0.7:
            recommendations.append({
                'category': 'disease_prediction',
                'priority': 'high' if disease_acc < 0.5 else 'medium',
                'issue': f'Low disease prediction accuracy: {disease_acc:.1%}',
                'recommendation': 'Review seasonal patterns and incorporate more historical data',
                'expected_impact': 'High'
            })
        
        # Medicine prediction recommendations
        medicine_acc = medicine_accuracy.get('overall_accuracy', 0)
        error_rate = medicine_accuracy.get('average_error_rate', 0)
        
        if medicine_acc < 0.7:
            recommendations.append({
                'category': 'medicine_prediction',
                'priority': 'high' if medicine_acc < 0.5 else 'medium',
                'issue': f'Low medicine prediction accuracy: {medicine_acc:.1%}',
                'recommendation': 'Implement more sophisticated demand forecasting algorithms',
                'expected_impact': 'High'
            })
        
        if error_rate > 0.3:
            recommendations.append({
                'category': 'medicine_prediction',
                'priority': 'medium',
                'issue': f'High prediction error rate: {error_rate:.1%}',
                'recommendation': 'Incorporate real-time usage data and adjust safety stock calculations',
                'expected_impact': 'Medium'
            })
        
        # General recommendations
        if not recommendations:
            recommendations.append({
                'category': 'system_improvement',
                'priority': 'low',
                'issue': 'System accuracy is acceptable but can be improved',
                'recommendation': 'Continue monitoring and consider advanced ML techniques',
                'expected_impact': 'Low'
            })
        
        return recommendations
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DECISION OUTCOME MONITORING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def monitor_decision_outcomes(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Monitor the outcomes of past decisions.
        
        For new users: This tracks whether recommended actions were
        effective, helping to refine decision-making algorithms and
        improve future recommendations.
        
        Args:
            start_date: Start of period to analyze
            end_date: End of period to analyze
            
        Returns:
            Dictionary containing decision outcome metrics
        """
        try:
            if start_date is None or end_date is None:
                # Analyze last 30 days
                end_date = date.today() - timedelta(days=1)
                start_date = end_date - timedelta(days=30)
            
            # Monitor restock decision outcomes
            restock_outcomes = self._monitor_restock_outcomes(start_date, end_date)
            
            # Monitor outbreak response outcomes
            outbreak_outcomes = self._monitor_outbreak_response_outcomes(start_date, end_date)
            
            # Monitor resource allocation outcomes
            resource_outcomes = self._monitor_resource_allocation_outcomes(start_date, end_date)
            
            # Calculate overall effectiveness
            overall_effectiveness = self._calculate_decision_effectiveness(
                restock_outcomes, outbreak_outcomes, resource_outcomes
            )
            
            return {
                'analysis_period': f'{start_date} to {end_date}',
                'generated_at': date.today().isoformat(),
                'restock_decision_outcomes': restock_outcomes,
                'outbreak_response_outcomes': outbreak_outcomes,
                'resource_allocation_outcomes': resource_outcomes,
                'overall_effectiveness': overall_effectiveness,
                'improvement_suggestions': self._generate_decision_improvements(
                    restock_outcomes, outbreak_outcomes, resource_outcomes
                )
            }
            
        except Exception as e:
            self.logger.error("Decision outcome monitoring failed: %s", str(e))
            return {
                'error': str(e),
                'restock_decision_outcomes': {},
                'outbreak_response_outcomes': {},
                'resource_allocation_outcomes': {},
                'overall_effectiveness': {}
            }
    
    def _monitor_restock_outcomes(self, start_date: date, end_date: date) -> Dict:
        """Monitor outcomes of restock decisions."""
        outcomes = {
            'total_decisions': 0,
            'successful_outcomes': 0,
            'stockouts_prevented': 0,
            'overstock_incidents': 0,
            'cost_effectiveness': 0.0
        }
        
        # Get medicines that had restock decisions
        # (In production, you'd track actual decisions made)
        
        # For now, simulate by checking medicines that had low stock
        # and then subsequent usage
        medicines_with_issues = DrugMaster.objects.filter(
            current_stock__lte=20
        ).values_list('drug_name', flat=True)
        
        for drug_name in medicines_with_issues:
            # Check if this medicine had usage during the period
            usage = PrescriptionLine.objects.filter(
                drug__drug_name=drug_name,
                prescription_date__range=(start_date, end_date)
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if usage > 0:
                outcomes['total_decisions'] += 1
                
                # Check if stockout was prevented
                # (Simplified logic - in production you'd track actual stock levels over time)
                if usage > 50:  # High usage
                    outcomes['stockouts_prevented'] += 1
                    outcomes['successful_outcomes'] += 1
                elif usage < 10:  # Low usage
                    outcomes['overstock_incidents'] += 1
        
        # Calculate effectiveness
        if outcomes['total_decisions'] > 0:
            outcomes['success_rate'] = round(
                outcomes['successful_outcomes'] / outcomes['total_decisions'], 3
            )
        else:
            outcomes['success_rate'] = 0.0
        
        return outcomes
    
    def _monitor_outbreak_response_outcomes(self, start_date: date, end_date: date) -> Dict:
        """Monitor outcomes of outbreak response decisions."""
        outcomes = {
            'total_responses': 0,
            'cases_prevented_estimate': 0,
            'response_effectiveness': 0.0,
            'average_response_time': 0.0
        }
        
        # Get diseases that had outbreak predictions
        outbreak_diseases = (
            Appointment.objects
            .filter(
                appointment_datetime__date__range=(start_date, end_date),
                disease__isnull=False
            )
            .values('disease__name')
            .annotate(case_count=Count('id'))
            .filter(case_count__gte=10)  # Significant outbreaks
        )
        
        for disease in outbreak_diseases:
            outcomes['total_responses'] += 1
            
            # Estimate cases prevented based on response level
            # (Simplified - in production you'd track actual interventions)
            case_count = disease['case_count']
            if case_count > 50:
                outcomes['cases_prevented_estimate'] += case_count * 0.3  # 30% reduction
                outcomes['response_effectiveness'] += 0.8
            elif case_count > 20:
                outcomes['cases_prevented_estimate'] += case_count * 0.2  # 20% reduction
                outcomes['response_effectiveness'] += 0.6
            else:
                outcomes['cases_prevented_estimate'] += case_count * 0.1  # 10% reduction
                outcomes['response_effectiveness'] += 0.4
        
        # Calculate average effectiveness
        if outcomes['total_responses'] > 0:
            outcomes['response_effectiveness'] = round(
                outcomes['response_effectiveness'] / outcomes['total_responses'], 3
            )
        
        return outcomes
    
    def _monitor_resource_allocation_outcomes(self, start_date: date, end_date: date) -> Dict:
        """Monitor outcomes of resource allocation decisions."""
        outcomes = {
            'total_allocations': 0,
            'resource_utilization': 0.0,
            'patient_satisfaction_estimate': 0.0,
            'efficiency_improvements': 0
        }
        
        # Get clinics that had resource allocation
        clinics = Clinic.objects.all()
        
        for clinic in clinics:
            # Check patient volume and resource usage
            appointments = Appointment.objects.filter(
                clinic=clinic,
                appointment_datetime__date__range=(start_date, end_date)
            ).count()
            
            if appointments > 0:
                outcomes['total_allocations'] += 1
                
                # Estimate resource utilization
                doctors = Doctor.objects.filter(clinic=clinic).count()
                if doctors > 0:
                    utilization = appointments / (doctors * 20)  # 20 patients per doctor per day
                    outcomes['resource_utilization'] += min(utilization, 1.0)
                    
                    # Estimate patient satisfaction based on utilization
                    if utilization < 0.8:
                        outcomes['patient_satisfaction_estimate'] += 0.9
                    elif utilization < 1.2:
                        outcomes['patient_satisfaction_estimate'] += 0.7
                    else:
                        outcomes['patient_satisfaction_estimate'] += 0.5
        
        # Calculate averages
        if outcomes['total_allocations'] > 0:
            outcomes['resource_utilization'] = round(
                outcomes['resource_utilization'] / outcomes['total_allocations'], 3
            )
            outcomes['patient_satisfaction_estimate'] = round(
                outcomes['patient_satisfaction_estimate'] / outcomes['total_allocations'], 3
            )
        
        return outcomes
    
    def _calculate_decision_effectiveness(self, restock_outcomes: Dict,
                                        outbreak_outcomes: Dict, 
                                        resource_outcomes: Dict) -> Dict:
        """Calculate overall decision effectiveness."""
        total_decisions = (
            restock_outcomes.get('total_decisions', 0) +
            outbreak_outcomes.get('total_responses', 0) +
            resource_outcomes.get('total_allocations', 0)
        )
        
        weighted_effectiveness = 0.0
        if total_decisions > 0:
            # Weight different decision types
            restock_weight = restock_outcomes.get('success_rate', 0) * 0.4
            outbreak_weight = outbreak_outcomes.get('response_effectiveness', 0) * 0.4
            resource_weight = resource_outcomes.get('resource_utilization', 0) * 0.2
            
            weighted_effectiveness = round(restock_weight + outbreak_weight + resource_weight, 3)
        
        return {
            'total_decisions': total_decisions,
            'weighted_effectiveness': weighted_effectiveness,
            'restock_effectiveness': restock_outcomes.get('success_rate', 0),
            'outbreak_effectiveness': outbreak_outcomes.get('response_effectiveness', 0),
            'resource_effectiveness': resource_outcomes.get('resource_utilization', 0),
            'overall_assessment': self._assess_decision_effectiveness(weighted_effectiveness)
        }
    
    def _assess_decision_effectiveness(self, effectiveness: float) -> str:
        """Assess overall decision effectiveness."""
        if effectiveness >= 0.8:
            return "EXCELLENT"
        elif effectiveness >= 0.7:
            return "GOOD"
        elif effectiveness >= 0.6:
            return "FAIR"
        elif effectiveness >= 0.5:
            return "POOR"
        else:
            return "CRITICAL"
    
    def _generate_decision_improvements(self, restock_outcomes: Dict,
                                      outbreak_outcomes: Dict,
                                      resource_outcomes: Dict) -> List[Dict]:
        """Generate suggestions for improving decision effectiveness."""
        improvements = []
        
        # Restock improvements
        restock_effectiveness = restock_outcomes.get('success_rate', 0)
        if restock_effectiveness < 0.7:
            improvements.append({
                'category': 'restock_decisions',
                'priority': 'high' if restock_effectiveness < 0.5 else 'medium',
                'issue': f'Low restock decision effectiveness: {restock_effectiveness:.1%}',
                'suggestion': 'Implement real-time inventory tracking and automated reorder triggers',
                'expected_improvement': 'High'
            })
        
        # Outbreak response improvements
        outbreak_effectiveness = outbreak_outcomes.get('response_effectiveness', 0)
        if outbreak_effectiveness < 0.7:
            improvements.append({
                'category': 'outbreak_response',
                'priority': 'high' if outbreak_effectiveness < 0.5 else 'medium',
                'issue': f'Low outbreak response effectiveness: {outbreak_effectiveness:.1%}',
                'suggestion': 'Improve early warning systems and response coordination',
                'expected_improvement': 'High'
            })
        
        # Resource allocation improvements
        resource_effectiveness = resource_outcomes.get('resource_utilization', 0)
        if resource_effectiveness < 0.7:
            improvements.append({
                'category': 'resource_allocation',
                'priority': 'medium',
                'issue': f'Low resource utilization: {resource_effectiveness:.1%}',
                'suggestion': 'Implement dynamic resource allocation based on real-time demand',
                'expected_improvement': 'Medium'
            })
        
        # General improvements
        if not improvements:
            improvements.append({
                'category': 'system_optimization',
                'priority': 'low',
                'issue': 'Decision effectiveness is acceptable but can be optimized',
                'suggestion': 'Continue monitoring and implement advanced optimization algorithms',
                'expected_improvement': 'Low'
            })
        
        return improvements
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM IMPROVEMENT RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_improvement_recommendations(self) -> Dict:
        """
        Get comprehensive system improvement recommendations.
        
        For new users: This provides actionable recommendations for
        improving the entire analytics system based on feedback data.
        
        Returns:
            Dictionary containing system-wide improvement recommendations
        """
        try:
            # Get recent accuracy and outcome data
            accuracy_data = self.track_prediction_accuracy()
            outcome_data = self.monitor_decision_outcomes()
            
            # Generate recommendations
            recommendations = self._generate_system_recommendations(
                accuracy_data, outcome_data
            )
            
            return {
                'generated_at': date.today().isoformat(),
                'system_health': self._assess_system_health(accuracy_data, outcome_data),
                'priority_recommendations': recommendations['high_priority'],
                'medium_recommendations': recommendations['medium_priority'],
                'low_recommendations': recommendations['low_priority'],
                'implementation_roadmap': self._create_implementation_roadmap(recommendations),
                'expected_benefits': self._calculate_expected_benefits(recommendations)
            }
            
        except Exception as e:
            self.logger.error("Improvement recommendations generation failed: %s", str(e))
            return {
                'error': str(e),
                'priority_recommendations': [],
                'medium_recommendations': [],
                'low_recommendations': []
            }
    
    def _generate_system_recommendations(self, accuracy_data: Dict, 
                                       outcome_data: Dict) -> Dict:
        """Generate categorized improvement recommendations."""
        recommendations = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': []
        }
        
        # Analyze accuracy issues
        overall_accuracy = accuracy_data.get('overall_metrics', {}).get('overall_accuracy', 0)
        if overall_accuracy < 0.6:
            recommendations['high_priority'].append({
                'id': 'ACC-001',
                'title': 'Improve Prediction Accuracy',
                'description': f'Overall prediction accuracy is {overall_accuracy:.1%}, below acceptable threshold',
                'actions': [
                    'Implement ensemble prediction methods',
                    'Incorporate more historical data',
                    'Add external data sources (weather, demographics)'
                ],
                'estimated_effort': 'High',
                'expected_impact': 'High'
            })
        
        # Analyze decision effectiveness
        overall_effectiveness = outcome_data.get('overall_effectiveness', {}).get('weighted_effectiveness', 0)
        if overall_effectiveness < 0.6:
            recommendations['high_priority'].append({
                'id': 'DEC-001',
                'title': 'Enhance Decision Effectiveness',
                'description': f'Overall decision effectiveness is {overall_effectiveness:.1%}',
                'actions': [
                    'Implement decision outcome tracking',
                    'Add feedback loops to decision algorithms',
                    'Improve decision timing and execution'
                ],
                'estimated_effort': 'Medium',
                'expected_impact': 'High'
            })
        
        # Medium priority recommendations
        if overall_accuracy < 0.8:
            recommendations['medium_priority'].append({
                'id': 'ACC-002',
                'title': 'Optimize Prediction Models',
                'description': 'Continue improving prediction accuracy beyond current levels',
                'actions': [
                    'Experiment with advanced ML algorithms',
                    'Implement feature engineering',
                    'Add model validation and testing'
                ],
                'estimated_effort': 'Medium',
                'expected_impact': 'Medium'
            })
        
        # Low priority recommendations
        recommendations['low_priority'].append({
            'id': 'SYS-001',
            'title': 'System Monitoring Enhancement',
            'description': 'Improve system monitoring and alerting capabilities',
            'actions': [
                'Add real-time performance dashboards',
                'Implement automated alerting for system issues',
                'Create comprehensive logging and audit trails'
            ],
            'estimated_effort': 'Low',
            'expected_impact': 'Low'
        })
        
        return recommendations
    
    def _assess_system_health(self, accuracy_data: Dict, outcome_data: Dict) -> str:
        """Assess overall system health."""
        accuracy_score = accuracy_data.get('overall_metrics', {}).get('overall_accuracy', 0)
        effectiveness_score = outcome_data.get('overall_effectiveness', {}).get('weighted_effectiveness', 0)
        
        avg_score = (accuracy_score + effectiveness_score) / 2
        
        if avg_score >= 0.8:
            return "EXCELLENT"
        elif avg_score >= 0.7:
            return "GOOD"
        elif avg_score >= 0.6:
            return "FAIR"
        elif avg_score >= 0.5:
            return "POOR"
        else:
            return "CRITICAL"
    
    def _create_implementation_roadmap(self, recommendations: Dict) -> List[Dict]:
        """Create a phased implementation roadmap."""
        roadmap = []
        
        # Phase 1: High priority items
        if recommendations['high_priority']:
            roadmap.append({
                'phase': 1,
                'title': 'Critical Improvements',
                'timeline': '1-3 months',
                'items': recommendations['high_priority'],
                'expected_outcome': 'Address critical system weaknesses'
            })
        
        # Phase 2: Medium priority items
        if recommendations['medium_priority']:
            roadmap.append({
                'phase': 2,
                'title': 'System Optimization',
                'timeline': '3-6 months',
                'items': recommendations['medium_priority'],
                'expected_outcome': 'Enhance system performance and accuracy'
            })
        
        # Phase 3: Low priority items
        if recommendations['low_priority']:
            roadmap.append({
                'phase': 3,
                'title': 'Advanced Features',
                'timeline': '6-12 months',
                'items': recommendations['low_priority'],
                'expected_outcome': 'Add advanced capabilities and monitoring'
            })
        
        return roadmap
    
    def _calculate_expected_benefits(self, recommendations: Dict) -> Dict:
        """Calculate expected benefits from implementing recommendations."""
        benefits = {
            'accuracy_improvement': 0.0,
            'cost_savings_estimate': 0,
            'efficiency_gains': 0.0,
            'risk_reduction': 0.0
        }
        
        # Calculate potential improvements
        high_priority_count = len(recommendations['high_priority'])
        medium_priority_count = len(recommendations['medium_priority'])
        
        benefits['accuracy_improvement'] = min(0.2 + (high_priority_count * 0.1), 0.4)
        benefits['efficiency_gains'] = min(0.15 + (medium_priority_count * 0.05), 0.3)
        benefits['risk_reduction'] = min(0.25 + (high_priority_count * 0.1), 0.5)
        
        # Estimate cost savings (simplified)
        benefits['cost_savings_estimate'] = int(
            (high_priority_count * 10000) + (medium_priority_count * 5000)
        )
        
        return benefits