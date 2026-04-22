from django.test import TestCase
from analytics.services.ml_engine import moving_average_forecast, weighted_trend_score, predict_demand

class MLMathTestCase(TestCase):
    """Mathematical robustness tests for the ML engine."""

    def test_moving_average_logic(self):
        # Normal
        self.assertEqual(moving_average_forecast([10, 10, 10]), 10.0)
        # Empty
        self.assertEqual(moving_average_forecast([]), 0.0)
        # Large window
        self.assertEqual(moving_average_forecast([0]*10 + [10]*3), 7.71) 
        # last_3 = [10,10,10] -> avg_3 = 10
        # last_7 = [0,0,0,0,10,10,10] -> avg_7 = 4.2857
        # forecast = 6 + 1.714 = 7.71


    def test_weighted_trend_score_math(self):
        self.assertEqual(weighted_trend_score(10, 0), 7.0)
        self.assertEqual(weighted_trend_score(0, 10), 3.0)
        self.assertEqual(weighted_trend_score(100, 100), 100.0)

    def test_predict_demand_math(self):
        self.assertEqual(predict_demand(100.0, 50.0), 150.0)
        self.assertEqual(predict_demand(0, 0), 0.0)

    def test_volatility_calculation(self):
        from analytics.services.ml_engine import calculate_volatility
        # Stable: [10, 10, 10] -> std=0, mean=10 -> CV=0
        self.assertEqual(calculate_volatility([10.0, 10.0, 10.0]), 0.0)
        # Volatile: [0, 100] -> mean=50, std=70.7 -> CV=1.414
        self.assertGreater(calculate_volatility([0.0, 100.0]), 1.0)
        # Insufficient data
        self.assertEqual(calculate_volatility([10.0]), 0.0)

