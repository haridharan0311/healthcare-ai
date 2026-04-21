import unittest
from django.test import TestCase
from analytics.services.ml_engine import (
    moving_average_forecast,
    exponential_smoothing_forecast,
    weighted_trend_score,
    time_decay_weight
)
from analytics.services.spike_detection import detect_spike_logic

class MLFunctionsTestCase(TestCase):
    """
    Comprehensive test suite for Machine Learning and Statistical functions.
    Covers edge cases, mathematical correctness, and robust error handling.
    """

    # ── Moving Average Forecast ──────────────────────────────────────
    
    def test_ma_basic_calculation(self):
        """Test standard weighted moving average calculation."""
        data = [10, 10, 10, 10, 10, 10, 10]
        self.assertEqual(moving_average_forecast(data), 10.0)

    def test_ma_trend_sensitivity(self):
        """Test if MA correctly responds to a rising trend."""
        data = [10, 11, 12, 13, 14, 15, 16]
        forecast = moving_average_forecast(data)
        self.assertGreater(forecast, 14.0) # Should be biased towards recent higher values

    def test_ma_empty_input(self):
        """Test behavior with empty list."""
        self.assertEqual(moving_average_forecast([]), 0.0)

    def test_ma_single_value(self):
        """Test behavior with single data point."""
        self.assertEqual(moving_average_forecast([5]), 5.0)

    def test_ma_window_clamping(self):
        """Test that weights don't exceed data length when data is small."""
        data = [10, 20]
        forecast = moving_average_forecast(data)
        self.assertEqual(forecast, 15.0)


    # ── Exponential Smoothing ───────────────────────────────────────

    def test_es_zero_variance(self):
        """Test ES with consistent data."""
        data = [100] * 10
        self.assertAlmostEqual(exponential_smoothing_forecast(data), 100.0, places=1)

        data = [10, 10, 10, 10, 10, 50, 50]
        # ES responds relative to alpha. Verify ES follows the increase.
        es_val = exponential_smoothing_forecast(data)
        self.assertGreater(es_val, 10.0)

    def test_es_empty_input(self):
        """Test ES with empty list."""
        self.assertEqual(exponential_smoothing_forecast([]), 0.0)


    # ── Spike Detection Logic (Z-Score) ─────────────────────────────

    def test_spike_detection_clear_outlier(self):
        """Test detection of a statistically significant spike."""
        # Mean: ~10, StdDev: low
        data = [10, 11, 9, 10, 12, 11, 50] 
        result = detect_spike_logic(data, z_threshold=2.0)
        self.assertTrue(result['is_spike'])
        self.assertGreater(result['z_score'], 2.0)

    def test_spike_detection_low_volume_filter(self):
        """Test that low counts don't trigger alerts if below min_volume."""
        # Even if 1 -> 4 is a big % jump, it shouldn't trigger if min_volume is 5
        data = [1, 1, 1, 1, 1, 1, 4]
        result = detect_spike_logic(data, min_volume=5)
        self.assertFalse(result['is_spike'])

    def test_spike_detection_zero_variance(self):
        """Test that constant data doesn't error out."""
        data = [10, 10, 10, 10, 10]
        result = detect_spike_logic(data)
        self.assertFalse(result['is_spike'])
        self.assertEqual(result['z_score'], 0)

    def test_spike_detection_insufficient_data(self):
        """Test with very few data points (fewer than 3)."""
        data = [10, 50]
        result = detect_spike_logic(data)
        self.assertFalse(result['is_spike'])
        self.assertEqual(result['status'], 'insufficient_data')


    # ── Trend Scoring & Decay ───────────────────────────────────────

    def test_weighted_trend_score_rising(self):
        """Test score with increasing cases."""
        # Recent: 20, Older: 10
        score = weighted_trend_score(20, 10)
        self.assertGreater(score, 0)

    def test_weighted_trend_score_calculation(self):
        """Test score comparison between rising and falling trends."""
        score_rising = weighted_trend_score(20, 5)
        score_falling = weighted_trend_score(5, 20)
        self.assertLess(score_falling, score_rising)

        w_recent = time_decay_weight(100, is_recent=True)
        w_older  = time_decay_weight(100, is_recent=False)
        self.assertGreater(w_recent, w_older)

if __name__ == '__main__':
    unittest.main()
