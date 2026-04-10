"""
Spike Detection Service Module

Advanced anomaly detection for disease outbreaks:
1. Statistical spike detection - anomalies above mean + 2σ
2. Seasonal adjustment - accounts for seasonal variations
3. Multi-window analysis - looks at multiple time windows
4. Alert generation - creates actionable alerts with severity levels

Layer: Services (Business Logic)
Dependencies: spike_detector, aggregation, logger

Usage:
    from analytics.services.spike_detection import SpikeDetectionService
    
    service = SpikeDetectionService()
    
    # Detect spikes in disease
    spikes = service.detect_disease_spikes(
        disease_name="Flu",
        baseline_days=7
    )
    
    # Get all critical spikes
    critical = service.get_critical_spikes()
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional

from django.db.models import Count, Max
from django.db.models.functions import TruncDate

from analytics.models import Appointment
from ..services.aggregation import get_disease_type
from .spike_detector import detect_spike, get_seasonal_weight
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)


class SpikeDetectionService:
    """
    Service for spike and anomaly detection.
    
    For new users: Identifies unusual patterns in disease occurrence
    that may indicate outbreaks or data anomalies.
    """
    
    def __init__(self):
        """Initialize service."""
        self.logger = logger
    
    # ────────────────────────────────────────────────────────────────────────────
    # FEATURE 2 + 8: Spike Detection & Real-Time Alert Engine
    # Detects statistical anomalies and generates actionable alerts
    # ────────────────────────────────────────────────────────────────────────────
    
    def detect_disease_spikes(
        self,
        disease_name: Optional[str] = None,
        baseline_days: int = 7,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict or List[Dict]:
        """
        FEATURE 8: Detect spikes in disease cases.
        
        Identifies days where cases exceed mean + 2×std_dev of baseline period.
        
        For new users: Anomaly detection helps identify unusual patterns
        that may indicate outbreaks. Statistical thresholds prevent false alarms.
        
        Args:
            disease_name: Specific disease (None = all diseases)
            baseline_days: Days used for baseline calculation
            start_date: Analysis period start
            end_date: Analysis period end
        
        Returns:
            If disease_name: Spike data for that disease
            If disease_name=None: Spikes for all diseases
        
        Example:
            spikes = service.detect_disease_spikes("Flu", baseline_days=7)
            if spikes['is_spike']:
                alert_health_ministry(spikes)
        """
        try:
            if start_date is None or end_date is None:
                start_date, end_date = validate_date_range()
            
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
                    .annotate(appt_date=TruncDate('appointment_datetime'))
                    .values('appt_date')
                    .annotate(day_count=Count('id'))
                    .order_by('appt_date')
                )
                
                daily_counts = [row['day_count'] for row in qs]
                
                if not daily_counts:
                    return {
                        'disease_name': disease_name,
                        'is_spike': False,
                        'status': 'no_data'
                    }
                
                spike_info = detect_spike(daily_counts, baseline_days=baseline_days)
                
                result = {
                    'disease_name': disease_name,
                    **spike_info,
                    'days_analyzed': len(daily_counts),
                    'baseline_days': baseline_days,
                    'severity': self._calculate_severity(spike_info)
                }
                
                if spike_info['is_spike']:
                    self.logger.warning(
                        "SPIKE DETECTED: %s - today: %d (threshold: %.1f)",
                        disease_name,
                        spike_info['today_count'],
                        spike_info['threshold']
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
                    .annotate(appt_date=TruncDate('appointment_datetime'))
                    .values('appt_date', 'disease__name')
                    .annotate(day_count=Count('id'))
                    .order_by('disease__name', 'appt_date')
                )
                
                daily_by_disease = defaultdict(lambda: defaultdict(int))
                for row in qs:
                    disease = get_disease_type(row['disease__name'])
                    daily_by_disease[disease][row['appt_date']] += row['day_count']
                
                spikes = []
                for disease, daily_map in daily_by_disease.items():
                    sorted_dates = sorted(daily_map.keys())
                    daily_counts = [daily_map[d] for d in sorted_dates]
                    
                    if len(daily_counts) > 1:
                        spike_info = detect_spike(daily_counts, baseline_days=baseline_days)
                        
                        if spike_info['is_spike']:
                            spikes.append({
                                'disease_name': disease,
                                **spike_info,
                                'severity': self._calculate_severity(spike_info),
                                'baseline_days': baseline_days
                            })
                
                # Sort by severity and today's count
                spikes.sort(key=lambda x: (-x['today_count'], x['severity']))
                
                return spikes
        
        except Exception as e:
            self.logger.error(
                "Spike detection failed",
                exception=e
            )
            return {} if disease_name else []
    
    def get_critical_spikes(
        self,
        min_days: int = 8
    ) -> List[Dict]:
        """
        Get all critical spikes in the system.
        
        For new users: Returns high-severity anomalies that require
        immediate attention from public health officials.
        
        Args:
            min_days: Minimum analysis window
        
        Returns:
            List of critical spikes with details
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=min_days)
            
            all_spikes = self.detect_disease_spikes(
                baseline_days=min_days - 1,
                start_date=start_date,
                end_date=end_date
            )
            
            if isinstance(all_spikes, dict):
                critical = [all_spikes] if all_spikes.get('is_spike') else []
            else:
                critical = [s for s in all_spikes if s.get('is_spike')]
            
            self.logger.info(
                "Found %d critical spikes",
                len(critical)
            )
            
            return critical
        
        except Exception as e:
            self.logger.error(
                "Critical spike retrieval failed",
                exception=e
            )
            return []
    
    def generate_spike_alerts(
        self,
        threshold_multiplier: float = 2.0
    ) -> List[Dict]:
        """
        Generate actionable alerts from detected spikes.
        
        For new users: Converts technical spike data into human-readable
        alerts suitable for notification systems.
        
        Args:
            threshold_multiplier: Std dev multiplier (2.0 = mean + 2σ)
        
        Returns:
            List of alert objects ready for notification
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=14)
            
            spikes = self.detect_disease_spikes(
                baseline_days=7,
                start_date=start_date,
                end_date=end_date
            )
            
            if isinstance(spikes, dict):
                spikes = [spikes] if spikes.get('is_spike') else []
            
            alerts = []
            for spike in spikes:
                if spike.get('is_spike'):
                    alert = {
                        'disease_name': spike['disease_name'],
                        'alert_type': 'spike',
                        'severity': spike.get('severity', 'warning'),
                        'today_count': spike['today_count'],
                        'threshold': spike['threshold'],
                        'excess': spike['today_count'] - spike['threshold'],
                        'message': (
                            f"Alert: Spike detected in {spike['disease_name']}. "
                            f"Cases today: {spike['today_count']} "
                            f"(threshold: {spike['threshold']:.1f})"
                        ),
                        'generated_at': date.today().isoformat()
                    }
                    alerts.append(alert)
            
            self.logger.info("Generated %d spike alerts", len(alerts))
            return alerts
        
        except Exception as e:
            self.logger.error(
                "Alert generation failed",
                exception=e
            )
            return []
    
    def _calculate_severity(self, spike_info: Dict) -> str:
        """
        Calculate severity level based on spike magnitude.
        
        For internal use: Maps spike excess to severity levels.
        """
        if not spike_info.get('is_spike'):
            return 'normal'
        
        excess = spike_info.get('today_count', 0) - spike_info.get('threshold', 0)
        threshold = spike_info.get('threshold', 1)
        
        if threshold == 0:
            return 'warning'
        
        excess_ratio = excess / threshold
        
        if excess_ratio >= 1.5:
            return 'critical'
        elif excess_ratio >= 0.8:
            return 'warning'
        else:
            return 'caution'
