import logging
from datetime import date, timedelta
from typing import List

from django.test import TestCase

# Internal Service Imports
from analytics.services.ml_engine import (
    moving_average_forecast, 
    weighted_trend_score, 
    predict_demand
)
from analytics.services.timeseries import get_seasonal_weight
from analytics.services.spike_detection import (
    detect_spike_logic as detect_spike,
    SpikeDetectionService
)
from analytics.services.restock_calculator import (
    calculate_restock, 
    apply_multi_disease_contribution,
    calculate_dynamic_safety_buffer
)
from analytics.services.aggregation import get_disease_type
from analytics.services.insights_service import InsightsService
from analytics.services.forecasting import ForecastingService

# Model Imports
from core.models import Clinic
from inventory.models import DrugMaster


class AnalyticsLogicTestCase(TestCase):
    """Base class for analytics logic tests with shared helpers."""
    
    def create_sequence(self, base_val: int, length: int, spike: int = None) -> List[int]:
        """Helper to create test sequences easily."""
        seq = [base_val] * length
        if spike is not None:
            seq[-1] = spike
        return seq


class TestMovingAverage(AnalyticsLogicTestCase):
    """Tests for the moving average forecasting engine."""

    def test_forecast_scenarios(self):
        # Case 1: Normal variation
        counts = [10, 12, 8, 15, 20, 18, 22, 25]
        self.assertAlmostEqual(moving_average_forecast(counts), 19.86, places=1)

        # Case 2: Empty/Minimal data
        self.assertEqual(moving_average_forecast([]), 0.0)
        self.assertEqual(moving_average_forecast([5]), 5.0)

        # Case 3: Zero activity
        self.assertEqual(moving_average_forecast([0, 0, 0]), 0.0)


class TestSpikeDetector(AnalyticsLogicTestCase):
    """Tests for statistical anomaly detection."""

    def test_detection_reliability(self):
        # Spike Scenario
        spike_seq = self.create_sequence(10, 7, spike=50)
        self.assertTrue(detect_spike(spike_seq)['is_spike'])

        # Stable Scenario
        stable_seq = self.create_sequence(10, 8)
        self.assertFalse(detect_spike(stable_seq)['is_spike'])

    def test_edge_cases(self):
        self.assertFalse(detect_spike([5])['is_spike']) # Insufficient data
        self.assertEqual(detect_spike([])['today_count'], 0)


class TestSeasonalWeights(AnalyticsLogicTestCase):
    """Tests for seasonal Intelligence."""

    def test_seasonal_adjustments(self):
        # Monsoon in August (Month 8) -> Active
        self.assertEqual(get_seasonal_weight("Monsoon", 8), 1.5)
        
        # Monsoon in January (Month 1) -> Inactive
        self.assertEqual(get_seasonal_weight("Monsoon", 1), 1.0)
        
        # Year-round diseases
        self.assertEqual(get_seasonal_weight("All", 6), 1.0)


class TestRestockCalculator(AnalyticsLogicTestCase):
    """Tests for inventory decision logic."""

    def test_restock_decision_matrix(self):
        # Scenario: High demand, low stock -> Critical Restock
        result = calculate_restock(
            drug_name='Paracetamol',
            generic_name='Acetaminophen',
            predicted_demand=100.0,
            avg_usage=2.0,
            current_stock=50,
            contributing_diseases=['Dengue']
        )
        self.assertEqual(result['status'], 'critical')
        self.assertEqual(result['suggested_restock'], 190)

        # Scenario: Zero stock -> Always Critical
        result_empty = calculate_restock(
            drug_name='A', generic_name='B', 
            predicted_demand=50.0, avg_usage=1.0, 
            current_stock=0, contributing_diseases=['C']
        )
        self.assertEqual(result_empty['status'], 'critical')


class TestDecisionSupportServices(AnalyticsLogicTestCase):
    """Integrated tests for high-level Decision Services."""

    def setUp(self):
        self.insights = InsightsService()
        self.forecasting = ForecastingService()

    def test_strategic_recommendations(self):
        """Verify that recommendations are logically triggered."""
        # Mocking an outbreak
        outbreaks = [{'disease': 'Flu', 'severity': 'Critical', 'message': 'Alert'}]
        actions = self.insights._generate_strategic_recommendations(
            outbreaks, [], [], {'adaptive_buffer': 1.2, 'interpretation': 'low_risk'}
        )
        self.assertTrue(any("emergency resources for Flu" in a for a in actions))

    def test_depletion_forecast_messages(self):
        """Verify depletion messaging based on urgency."""
        # Critical urgency
        msg_crit = self.forecasting._get_depletion_recommendation('critical', 3.5)
        self.assertIn("Action Required", msg_crit)
        
        # Low urgency
        msg_low = self.forecasting._get_depletion_recommendation('low', 12.0)
        self.assertIn("Order Soon", msg_low)
