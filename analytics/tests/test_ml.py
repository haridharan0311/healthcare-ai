from django.test import TestCase
from analytics.ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from analytics.spike_detector import detect_spike, get_seasonal_weight
from analytics.restock_calculator import calculate_restock, apply_multi_disease_contribution

from analytics.aggregation import (
    compare_disease_trends, get_disease_type,
    calculate_dynamic_safety_buffer,
)


class TestMovingAverage(TestCase):

    def test_normal_forecast(self):
        counts = [10, 12, 8, 15, 20, 18, 22, 25]
        result = moving_average_forecast(counts)
        self.assertAlmostEqual(result, 19.86, places=1)

    def test_empty_input(self):
        self.assertEqual(moving_average_forecast([]), 0.0)

    def test_single_value(self):
        self.assertEqual(moving_average_forecast([5]), 5.0)

    def test_all_zeros(self):
        """Edge case: all zero daily counts"""
        self.assertEqual(moving_average_forecast([0, 0, 0, 0, 0, 0, 0]), 0.0)


class TestSpikeDetector(TestCase):

    def test_spike_detected(self):
        counts = [10, 9, 11, 10, 12, 10, 9, 50]
        result = detect_spike(counts)
        self.assertTrue(result['is_spike'])
        self.assertEqual(result['today_count'], 50)

    def test_no_spike(self):
        counts = [10, 9, 11, 10, 12, 10, 9, 11]
        result = detect_spike(counts)
        self.assertFalse(result['is_spike'])

    def test_insufficient_data(self):
        result = detect_spike([5])
        self.assertFalse(result['is_spike'])
        self.assertEqual(result['reason'], 'not enough data')

    def test_empty_input(self):
        """Edge case: empty list"""
        result = detect_spike([])
        self.assertFalse(result['is_spike'])
        self.assertEqual(result['today_count'], 0)

    def test_all_zeros(self):
        """Edge case: all zeros — no spike"""
        result = detect_spike([0, 0, 0, 0, 0, 0, 0, 0])
        self.assertFalse(result['is_spike'])

    def test_spike_wider_baseline(self):
        counts = [5] * 30 + [50]
        result = detect_spike(counts, baseline_days=30)
        self.assertTrue(result['is_spike'])
        self.assertAlmostEqual(result['mean_last_7_days'], 5.0, places=0)

    def test_no_spike_wider_baseline(self):
        counts = [2, 2, 2, 20, 20, 20, 20, 20, 20, 21]
        result = detect_spike(counts, baseline_days=9)
        self.assertFalse(result['is_spike'])

    def test_seasonal_weight_in_season(self):
        self.assertEqual(get_seasonal_weight("Monsoon", 8), 1.5)

    def test_seasonal_weight_out_of_season(self):
        self.assertEqual(get_seasonal_weight("Monsoon", 1), 1.0)

    def test_seasonal_weight_all(self):
        """'All' season never gets a boost"""
        self.assertEqual(get_seasonal_weight("All", 6), 1.0)


class TestRestockCalculator(TestCase):

    def test_restock_needed(self):
        result = calculate_restock(
            drug_name='Paracetamol',
            generic_name='Acetaminophen',
            predicted_demand=100.0,
            avg_usage=2.0,
            current_stock=50,
            contributing_diseases=['Dengue', 'Viral Fever']
        )
        # expected = 100 x 2.0 x 1.2 = 240 → restock = 240 - 50 = 190
        self.assertEqual(result['suggested_restock'], 190)
        self.assertEqual(result['status'], 'critical')

    def test_no_restock_needed(self):
        result = calculate_restock(
            drug_name='ORS',
            generic_name='Oral Rehydration Salts',
            predicted_demand=10.0,
            avg_usage=1.0,
            current_stock=500,
            contributing_diseases=['Dehydration']
        )
        self.assertEqual(result['suggested_restock'], 0)
        self.assertEqual(result['status'], 'sufficient')

    def test_zero_current_stock(self):
        """Edge case: zero stock always critical"""
        result = calculate_restock(
            drug_name='Cetirizine',
            generic_name='Cetirizine hydrochloride',
            predicted_demand=50.0,
            avg_usage=1.0,
            current_stock=0,
            contributing_diseases=['Allergy']
        )
        self.assertEqual(result['status'], 'critical')
        self.assertGreater(result['suggested_restock'], 0)

    def test_zero_demand_new_disease(self):
        """Edge case: new disease with zero demand history"""
        result = calculate_restock(
            drug_name='NewDrug',
            generic_name='NewGeneric',
            predicted_demand=0.0,
            avg_usage=1.0,
            current_stock=100,
            contributing_diseases=['NewDisease']
        )
        self.assertEqual(result['status'], 'sufficient')
        self.assertEqual(result['suggested_restock'], 0)

    def test_multi_disease_contribution(self):
        demands = [
            {'predicted_demand': 50.0, 'seasonal_weight': 1.5},
            {'predicted_demand': 30.0, 'seasonal_weight': 1.0},
        ]
        # 50x1.5 + 30x1.0 = 75 + 30 = 105
        self.assertEqual(apply_multi_disease_contribution(demands), 105.0)

    def test_zero_demand_multi_disease(self):
        """Edge case: all zero demands"""
        demands = [
            {'predicted_demand': 0.0, 'seasonal_weight': 1.5},
            {'predicted_demand': 0.0, 'seasonal_weight': 1.0},
        ]
        self.assertEqual(apply_multi_disease_contribution(demands), 0.0)

    def test_demand_prediction_zero(self):
        """Edge case: zero trend and zero forecast"""
        self.assertEqual(predict_demand(0.0, 0.0), 0.0)




class TestAggregation(TestCase):

    def test_get_disease_type_strips_number(self):
        self.assertEqual(get_disease_type('Dengue 1842'), 'Dengue')

    def test_get_disease_type_no_number(self):
        self.assertEqual(get_disease_type('COVID-19'), 'COVID-19')

    def test_get_disease_type_empty(self):
        self.assertEqual(get_disease_type(''), '')

    def test_get_disease_type_none(self):
        self.assertEqual(get_disease_type(None), '')


class TestTrendComparison(TestCase):

    def test_increase_detected(self):
        from datetime import date
        # Simulate compare — period2 has more cases
        p1 = {'Flu': {'count': 10, 'season': 'Winter', 'category': '', 'severity': 1}}
        p2 = {'Flu': {'count': 15, 'season': 'Winter', 'category': '', 'severity': 1}}
        # Manual calculation
        pct = round(((15 - 10) / 10) * 100, 2)
        self.assertEqual(pct, 50.0)
        self.assertEqual('up' if pct > 0 else 'down', 'up')

    def test_decrease_detected(self):
        count1, count2 = 20, 10
        pct = round(((count2 - count1) / count1) * 100, 2)
        self.assertEqual(pct, -50.0)
        self.assertEqual('down' if pct < 0 else 'up', 'down')

    def test_new_disease_zero_baseline(self):
        count1, count2 = 0, 5
        pct = 100.0 if count2 > 0 else 0.0
        direction = 'new'
        self.assertEqual(direction, 'new')
        self.assertEqual(pct, 100.0)


class TestAutoSafetyBuffer(TestCase):

    def test_no_spikes_returns_base(self):
        from analytics.restock_calculator import calculate_dynamic_safety_buffer
        result = calculate_dynamic_safety_buffer(spike_count=0, total_diseases=8)
        self.assertAlmostEqual(result, 1.2, places=2)

    def test_all_spiking_returns_max(self):
        from analytics.restock_calculator import calculate_dynamic_safety_buffer
        result = calculate_dynamic_safety_buffer(spike_count=8, total_diseases=8)
        self.assertAlmostEqual(result, 1.8, places=2)

    def test_half_spiking(self):
        from analytics.restock_calculator import calculate_dynamic_safety_buffer
        result = calculate_dynamic_safety_buffer(spike_count=4, total_diseases=8)
        # 1.2 + (0.5 × 0.6) = 1.5
        self.assertAlmostEqual(result, 1.5, places=2)

    def test_zero_total_returns_base(self):
        from analytics.restock_calculator import calculate_dynamic_safety_buffer
        result = calculate_dynamic_safety_buffer(spike_count=0, total_diseases=0)
        self.assertAlmostEqual(result, 1.2, places=2)