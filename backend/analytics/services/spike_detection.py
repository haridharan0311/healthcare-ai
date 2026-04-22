"""
Layer 3: Prediction - Spike Detection & Outbreak Analysis

Provides advanced anomaly detection for disease outbreaks:
1. Statistical Spike Detection - Identifies anomalies above (mean + 2σ).
2. Consistent Trend Detection - FEATURE 2: Early Outbreak Warning System.
3. Severity Intelligence - Calculates impact based on magnitude.

Usage:
    from analytics.services.spike_detection import SpikeDetectionService
    
    service = SpikeDetectionService()
    spikes = service.detect_disease_spikes("Flu")
    outbreaks = service.detect_early_outbreaks()
"""

import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional

from django.db.models import Count
from django.db.models.functions import TruncDate

from analytics.models import Appointment
from .aggregation import get_disease_type
from ..utils.logger import get_logger
from ..utils.validators import validate_date_range

logger = get_logger(__name__)

def detect_spike_logic(daily_counts: List[int], baseline_days: int = 7, z_threshold: float = 2.0, min_volume: int = 3) -> Dict:
    """
    Statistical spike detection using Z-score and historical variability.
    - z_threshold: Z-score threshold for alert (default 2.0 for 95% confidence)
    - min_volume: Minimum absolute cases required to trigger an alert
    """
    if len(daily_counts) < 3:
        return {
            "today_count": daily_counts[-1] if daily_counts else 0,
            "mean_last_7_days": 0.0,
            "std_dev": 0.0,
            "threshold": 0.0,
            "is_spike": False,
            "confidence": 0.0,
            "impact_severity": "normal",
            "status": "insufficient_data",
            "reason": "insufficient data window"
        }

    today = daily_counts[-1]
    baseline = daily_counts[-(baseline_days + 1):-1] if len(daily_counts) >= baseline_days + 1 else daily_counts[:-1]

    mean = statistics.mean(baseline) if baseline else 0.0
    std_dev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
    
    # Use a minimum standard deviation to avoid division by zero and false positives in low-volume
    effective_std_dev = max(std_dev, 0.5) 
    z_score = (today - mean) / effective_std_dev
    
    # Threshold: Z-score > z_threshold is usually considered an anomaly
    threshold = mean + (z_threshold * effective_std_dev)
    is_spike = z_score > z_threshold and today >= min_volume
    
    # Confidence Scoring
    cv = (std_dev / mean) if mean > 0 else 1.0
    consistency_score = max(0, 1.0 - cv)
    volume_score = min(len(baseline) / baseline_days, 1.0)
    confidence = round((consistency_score * 0.4 + volume_score * 0.6), 2)
    
    # Severity assessment
    severity = "normal"
    if is_spike:
        if z_score > 4.0: severity = "critical"
        elif z_score > 3.0: severity = "warning"
        else: severity = "mild"

    return {
        "today_count": today,
        "mean_last_7_days": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "z_score": round(z_score, 2),
        "threshold": round(threshold, 2),
        "is_spike": is_spike,
        "confidence": confidence,
        "impact_severity": severity,
        "status": "success"
    }


class SpikeDetectionService:
    """Service for early outbreak and anomaly detection."""
    
    def __init__(self):
        self.logger = logger

    def detect_disease_spikes(self, disease_name: Optional[str] = None, days: int = 14) -> List[Dict]:
        """Detect statistical spikes."""
        start_date = date.today() - timedelta(days=days)
        qs = Appointment.objects.filter(
            appointment_datetime__date__gte=start_date,
            disease__isnull=False
        )
        if disease_name:
            qs = qs.filter(disease__name__icontains=disease_name)
            
        qs = qs.select_related('disease').annotate(day=TruncDate('appointment_datetime')).values('day', 'disease__name').annotate(count=Count('id')).order_by('disease__name', 'day')
        
        disease_data = defaultdict(list)
        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            disease_data[dtype].append(row['count'])
            
        results = []
        for dtype, counts in disease_data.items():
            spike = detect_spike_logic(counts)
            if spike['is_spike']:
                results.append({
                    'disease_name': dtype,
                    **spike,
                    'severity': 'critical' if spike['today_count'] > spike['threshold'] * 1.5 else 'warning'
                })
        return results

    def detect_early_outbreaks(self, min_days: int = 3, min_cases: int = 5) -> List[Dict]:
        """
        FEATURE 2: Early Outbreak Warning System.
        Detects consistent upward trends in multi-day windows.
        Uses a sliding window to detect if a disease is consistently rising.
        """
        start_date = date.today() - timedelta(days=14)
        qs = Appointment.objects.filter(
            appointment_datetime__date__gte=start_date,
            disease__isnull=False
        ).select_related('disease').annotate(day=TruncDate('appointment_datetime')).values('day', 'disease__name').annotate(count=Count('id')).order_by('disease__name', 'day')
        
        disease_series = defaultdict(list)
        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            disease_series[dtype].append(row['count'])
            
        outbreaks = []
        for dtype, counts in disease_series.items():
            if len(counts) < min_days: continue
            
            # Check for consecutive growth in the last N days (Feature 2)
            recent = counts[-min_days:]
            
            # Robust trend check: Either strictly increasing OR significantly higher than average
            strictly_increasing = all(recent[i] < recent[i+1] for i in range(len(recent)-1))
            
            # Calculate slope (simple)
            if len(recent) >= 2:
                slope = (recent[-1] - recent[0]) / (len(recent) - 1)
            else:
                slope = 0

            if (strictly_increasing or slope > 1.0) and recent[-1] >= min_cases:
                # Scoring logic for Feature 2
                growth_multiplier = recent[-1] / recent[0] if recent[0] > 0 else recent[-1]
                score = (growth_multiplier * 50) + (len(recent) * 10) + (slope * 5)
                
                outbreaks.append({
                    'disease_name': dtype,
                    'trend_days': len(recent),
                    'start_count': recent[0],
                    'end_count': recent[-1],
                    'slope': round(slope, 2),
                    'growth_multiplier': round(growth_multiplier, 2),
                    'impact_score': round(score, 1),
                    'severity': 'critical' if score > 100 else 'warning',
                    'message': f"Early Outbreak Alert: Consistent upward trend detected for {dtype} ({round(growth_multiplier*100-100, 1)}% total growth)."
                })
        return sorted(outbreaks, key=lambda x: x['impact_score'], reverse=True)
    def generate_spike_alerts(self) -> List[Dict]:
        """Convenience method for getting latest spike alerts (Fixed 8-day window)."""
        return self.detect_disease_spikes(days=8)
