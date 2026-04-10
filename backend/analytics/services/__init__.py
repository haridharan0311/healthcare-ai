"""
Analytics Services Package

This package implements a layered architecture for healthcare analytics:

Layer 1: Data Aggregation (aggregation.py)
  - Pure ORM queries for data retrieval
  - No business logic, just data access

Layer 2: Analytics Engine (analytics_engine.py)
  - Centralized analytics computations
  - Time-series analysis, pattern recognition
  - Statistical computations

Layer 3: Prediction Engine (prediction_engine.py)
  - ML-based forecasting
  - Demand prediction
  - Trend analysis

Layer 4: Decision Engine (decision_engine.py)
  - Business rule evaluation
  - Alert generation
  - Recommendation generation

Layer 5: API Layer (views/)
  - RESTful endpoints
  - Response formatting
  - Caching and optimization
"""

from .analytics_engine import AnalyticsEngine
from .prediction_engine import PredictionEngine
from .decision_engine import DecisionEngine
from .feedback_engine import FeedbackEngine
from .medicine_analytics import MedicineAnalyticsService
from .restock_service import RestockService

__all__ = [
    'AnalyticsEngine',
    'PredictionEngine', 
    'DecisionEngine',
    'FeedbackEngine',
    'MedicineAnalyticsService',
    'RestockService',
]
