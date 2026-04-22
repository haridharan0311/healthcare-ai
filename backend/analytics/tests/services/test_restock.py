from datetime import date, timedelta
from django.test import TestCase
from analytics.services.restock_service import RestockService

class RestockServiceTestCase(TestCase):
    """Feature 5: Adaptive Safety Buffer tests."""

    def test_adaptive_buffer_calculation(self):
        service = RestockService()
        # Stable usage
        # Mapping mock daily data
        today = date.today()
        daily = {"Flu": {today: 10, today - timedelta(days=1): 10}}
        res = service.calculate_adaptive_buffer(daily_by_disease=daily)
        # Base multiplier is 1.2 (20% above 1.0)
        self.assertEqual(res['adaptive_buffer'], 1.2) 

