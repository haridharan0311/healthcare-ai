from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from analytics.services.forecasting import ForecastingService
from analytics.services.restock_service import RestockService
from analytics.models import Disease
from inventory.models import DrugMaster
from core.models import Clinic

class AnalyticsRobustnessTestCase(TestCase):
    """
    Robustness tests for checking service behavior with edge-case data (e.g. zero records).
    """

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Alpha", clinic_address_1="Central")
        self.disease = Disease.objects.create(
            name="Rare Flu", 
            season="SUMMER", 
            severity=2,
            created_at=timezone.now()
        )
        self.forecasting = ForecastingService()
        self.restock = RestockService()

    def test_forecasting_with_zero_data(self):
        """Verify that ForecastingService handles diseases with no historical data gracefully."""
        # Test forecast_next_period for a disease with 0 appointments
        res = self.forecasting.forecast_next_period("Rare Flu", days_ahead=7)
        
        self.assertEqual(res['forecast_value'], 0)
        self.assertEqual(res['status'], 'insufficient_data')
        self.assertEqual(res['days_available'], 0)

    def test_restock_suggestions_with_no_usage(self):
        """Verify that RestockService handles drugs with zero usage history."""
        DrugMaster.objects.create(
            drug_name="New Drug",
            drug_strength="10mg",
            dosage_type="Tablet",
            current_stock=50,
            clinic=self.clinic
        )
        
        start = date.today() - timedelta(days=30)
        end = date.today()
        
        # Should run without crashing and return results (with suggested_restock potentially 0)
        suggestions = self.restock.calculate_restock_suggestions(start, end)
        
        # Filter for our new drug
        drug_suggestion = next((s for s in suggestions if s['drug_name'] == "New Drug"), None)
        
        # If there's no usage, demand should be 0, and suggested_restock should be 0 if current_stock > safety_buffer
        if drug_suggestion:
            self.assertEqual(drug_suggestion['predicted_demand'], 0)
            self.assertEqual(drug_suggestion['suggested_restock'], 0)

    def test_forecast_all_diseases_empty_db(self):
        """Verify bulk forecasting works even with an empty database."""
        # Empty all appointments (already empty in this fresh test method)
        results = self.forecasting.forecast_all_diseases(days_ahead=7)
        self.assertEqual(len(results), 0)
