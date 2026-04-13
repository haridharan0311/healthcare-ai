"""
Analytics Services Package - Simple Flow
========================================
Consolidated services for healthcare analytics.
"""

from .dashboard_service import DashboardService
from .restock_service import RestockService
from .timeseries import TimeSeriesAnalysis
from .usage import UsageIntelligence
from .spike_detection import SpikeDetectionService
from .forecasting import ForecastingService

__all__ = [
    'DashboardService',
    'RestockService',
    'TimeSeriesAnalysis',
    'UsageIntelligence',
    'SpikeDetectionService',
    'ForecastingService',
]
