import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional, Any

from django.db.models import Count, QuerySet
from django.db.models.functions import TruncDate

from analytics.models import Appointment
from .aggregation import get_disease_type
from ..utils.logger import get_logger
from .constants import (
    Z_SCORE_THRESHOLD,
    MIN_SPIKE_VOLUME,
    BASELINE_DAYS,
    MIN_STD_DEV,
    SPIKE_CRITICAL_Z,
    SPIKE_WARNING_Z,
    OUTBREAK_MIN_DAYS,
    OUTBREAK_MIN_CASES,
    OUTBREAK_SCORE_CRITICAL,
    DEFAULT_LOOKBACK_DAYS
)

logger = get_logger(__name__)

def detect_spike_logic(
    daily_counts: List[int], 
    baseline_days: int = BASELINE_DAYS, 
    z_threshold: float = Z_SCORE_THRESHOLD, 
    min_volume: int = MIN_SPIKE_VOLUME
) -> Dict[str, Any]:
    """
    Statistical spike detection using Z-score and historical variability.
    - z_threshold: Z-score threshold for alert (default 2.0 for 95% confidence)
    - min_volume: Minimum absolute cases required to trigger an alert
    """
    if len(daily_counts) < 3:
        return {
            "today_count": daily_counts[-1] if daily_counts else 0,
            "is_spike": False,
            "status": "insufficient_data",
            "reason": "insufficient data window"
        }

    today = daily_counts[-1]
    # Use previous N days as baseline (excluding today)
    baseline = daily_counts[-(baseline_days + 1):-1] if len(daily_counts) >= baseline_days + 1 else daily_counts[:-1]

    mean = statistics.mean(baseline) if baseline else 0.0
    std_dev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
    
    # Use a minimum standard deviation to avoid division by zero and false positives in low-volume
    effective_std_dev = max(std_dev, MIN_STD_DEV) 
    z_score = (today - mean) / effective_std_dev
    
    # Threshold: Z-score > z_threshold is usually considered an anomaly
    threshold = mean + (z_threshold * effective_std_dev)
    is_spike = z_score > z_threshold and today >= min_volume
    
    # Confidence Scoring: Combination of consistency (CV) and data volume
    cv = (std_dev / mean) if mean > 0 else 1.0
    consistency_score = max(0, 1.0 - cv)
    volume_score = min(len(baseline) / baseline_days, 1.0)
    confidence = round((consistency_score * 0.4 + volume_score * 0.6), 2)
    
    # Severity assessment based on standard deviation distance
    severity = "normal"
    if is_spike:
        if z_score > SPIKE_CRITICAL_Z: severity = "critical"
        elif z_score > SPIKE_WARNING_Z: severity = "warning"
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

    def _get_disease_time_series(self, days: int, disease_name: Optional[str] = None) -> Dict[str, List[int]]:
        """Internal helper to fetch time series data efficiently with aggregation."""
        start_date = date.today() - timedelta(days=days)
        qs_base = Appointment.objects.filter(
            appointment_datetime__date__gte=start_date,
            disease__isnull=False
        )
        if disease_name:
            qs_base = qs_base.filter(disease__name__icontains=disease_name)
            
        qs = (
            qs_base.annotate(day=TruncDate('appointment_datetime'))
            .values('day', 'disease__name')
            .annotate(count=Count('id'))
            .order_by('disease__name', 'day')
        )
        
        disease_data = defaultdict(list)
        for row in qs:
            dtype = get_disease_type(row['disease__name'])
            disease_data[dtype].append(row['count'])
        return disease_data

    def detect_disease_spikes(self, disease_name: Optional[str] = None, days: int = 14) -> List[Dict[str, Any]]:
        """Detect statistical spikes across all diseases or a specific one."""
        try:
            disease_data = self._get_disease_time_series(days, disease_name)
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
        except Exception as e:
            self.logger.error(f"Spike detection failed: {str(e)}", exc_info=True)
            return []

    def detect_early_outbreaks(self, min_days: int = OUTBREAK_MIN_DAYS, min_cases: int = OUTBREAK_MIN_CASES) -> List[Dict[str, Any]]:
        """
        FEATURE 2: Early Outbreak Warning System.
        Detects consistent upward trends in multi-day windows.
        """
        try:
            # Use a slightly longer window for outbreak trend analysis
            disease_series = self._get_disease_time_series(DEFAULT_LOOKBACK_DAYS // 2) 
            outbreaks = []
            
            for dtype, counts in disease_series.items():
                if len(counts) < min_days:
                    continue
                
                recent = counts[-min_days:]
                
                # Robust trend check: Consistent growth
                strictly_increasing = all(recent[i] < recent[i+1] for i in range(len(recent)-1))
                
                # Simple linear slope
                slope = (recent[-1] - recent[0]) / (len(recent) - 1) if len(recent) >= 2 else 0

                if (strictly_increasing or slope > 1.0) and recent[-1] >= min_cases:
                    growth_multiplier = recent[-1] / recent[0] if recent[0] > 0 else recent[-1]
                    
                    # Scoring logic: Growth (50%) + Continuity (30%) + Slope (20%)
                    score = (growth_multiplier * 50) + (len(recent) * 10) + (slope * 5)
                    
                    outbreaks.append({
                        'disease_name': dtype,
                        'trend_days': len(recent),
                        'start_count': recent[0],
                        'end_count': recent[-1],
                        'impact_score': round(score, 1),
                        'severity': 'critical' if score > OUTBREAK_SCORE_CRITICAL else 'warning',
                        'message': f"Early Outbreak Alert: Consistent upward trend detected for {dtype} ({round(growth_multiplier*100-100, 1)}% total growth)."
                    })
            return sorted(outbreaks, key=lambda x: x['impact_score'], reverse=True)
        except Exception as e:
            self.logger.error(f"Outbreak detection failed: {str(e)}", exc_info=True)
            return []

    def generate_spike_alerts(self) -> List[Dict[str, Any]]:
        """Convenience method for latest spike alerts (Fixed 8-day window)."""
        return self.detect_disease_spikes(days=8)
