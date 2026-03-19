from django.test import TestCase
from analytics.ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from analytics.spike_detector import detect_spike, get_seasonal_weight
from analytics.restock_calculator import calculate_restock, apply_multi_disease_contribution


class TestMovingAverage(TestCase):

    def test_normal_forecast(self):
        counts = [10, 12, 8, 15, 20, 18, 22, 25]
        result = moving_average_forecast(counts)
        # last_3_avg = (18+22+25)/3 = 21.67, last_7_avg = (12+8+15+20+18+22+25)/7 = 17.14
        # forecast = 21.67×0.6 + 17.14×0.4 = 13.0 + 6.86 = 19.86
        self.assertAlmostEqual(result, 19.86, places=1)

    def test_empty_input(self):
        self.assertEqual(moving_average_forecast([]), 0.0)

    def test_single_value(self):
        result = moving_average_forecast([5])
        self.assertEqual(result, 5.0)


class TestSpikeDetector(TestCase):

    def test_spike_detected(self):
        # Baseline is stable around 10, today jumps to 50
        counts = [10, 9, 11, 10, 12, 10, 9, 50]
        result = detect_spike(counts)
        self.assertTrue(result["is_spike"])
        self.assertEqual(result["today_count"], 50)

    def test_no_spike(self):
        counts = [10, 9, 11, 10, 12, 10, 9, 11]
        result = detect_spike(counts)
        self.assertFalse(result["is_spike"])

    def test_insufficient_data(self):
        result = detect_spike([5])
        self.assertFalse(result["is_spike"])
        self.assertEqual(result["reason"], "not enough data")

    def test_seasonal_weight_in_season(self):
        weight = get_seasonal_weight("Monsoon", current_month=8)  # August
        self.assertEqual(weight, 1.5)

    def test_seasonal_weight_out_of_season(self):
        weight = get_seasonal_weight("Monsoon", current_month=1)  # January
        self.assertEqual(weight, 1.0)

    # Add a new test for wider baseline
    def test_spike_wider_baseline(self):
        # 30-day baseline: stable ~5/day, spike at 50
        counts = [5] * 30 + [50]
        result = detect_spike(counts, baseline_days=30)
        self.assertTrue(result["is_spike"])
        # Mean should be close to 5, not just last 7 days
        self.assertAlmostEqual(result["mean_last_7_days"], 5.0, places=0)

    def test_no_spike_wider_baseline(self):
        # If recent days were also high, wider baseline raises threshold
        counts = [2, 2, 2, 20, 20, 20, 20, 20, 20, 21]
        result = detect_spike(counts, baseline_days=9)
        # mean of 9 baseline days includes the high values → threshold higher
        self.assertFalse(result["is_spike"])


class TestRestockCalculator(TestCase):

    def test_restock_needed(self):
        result = calculate_restock(
            drug_name="Paracetamol",
            generic_name="Acetaminophen",
            predicted_demand=100.0,
            avg_quantity_per_prescription=2.0,
            current_stock=50,
            contributing_diseases=["Dengue", "Viral Fever"]
        )
        # expected_demand = 100 × 2.0 × 1.2 = 240
        # suggested_restock = 240 - 50 = 190
        self.assertEqual(result["suggested_restock"], 190)
        self.assertEqual(result["status"], "critical")

    def test_no_restock_needed(self):
        result = calculate_restock(
            drug_name="ORS",
            generic_name="Oral Rehydration Salts",
            predicted_demand=10.0,
            avg_quantity_per_prescription=1.0,
            current_stock=500,
            contributing_diseases=["Dehydration"]
        )
        self.assertEqual(result["suggested_restock"], 0)
        self.assertEqual(result["status"], "sufficient")

    def test_multi_disease_contribution(self):
        demands = [
            {"predicted_demand": 50.0, "seasonal_weight": 1.5},
            {"predicted_demand": 30.0, "seasonal_weight": 1.0},
        ]
        total = apply_multi_disease_contribution(demands)
        # 50×1.5 + 30×1.0 = 75 + 30 = 105
        self.assertEqual(total, 105.0)

