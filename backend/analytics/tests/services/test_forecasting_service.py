import json
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User

from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.services.forecasting import ForecastingService
from analytics.services.timeseries import TimeSeriesAnalysis

class ForecastingServiceTestCase(TestCase):
    """Tests for forecasting and time-series services (Features 1, 2, 4, 6)."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Forecast Clinic")
        self.admin = User.objects.create_superuser(username="admin_forecast", password="pw")
        UserProfile.objects.create(user=self.admin, role="ADMIN")
        
        self.disease = Disease.objects.create(name="Seasonal Flu", season="Winter")
        self.doctor = Doctor.objects.create(first_name="DrF", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="PatF", dob="2000-01-01", clinic=self.clinic)
        self.service = ForecastingService()

    def test_growth_rate_calculation(self):
        """Feature 1: Test Disease Growth Rate Indicator."""
        ts = TimeSeriesAnalysis()
        # Seed 10 cases last week
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=2),
                disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
                op_number=f"G1-{i}"
            )
        # Seed 20 cases this week
        for i in range(20):
            Appointment.objects.create(
                appointment_datetime=timezone.now(),
                disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
                op_number=f"G2-{i}"
            )
        
        res = ts.calculate_growth_rate("Seasonal Flu", days=7)
        self.assertEqual(res['growth_rate'], 100.0)
        self.assertEqual(res['direction'], 'up')

    def test_early_outbreak_detection(self):
        """Feature 2: Test Early Outbreak Detection (Monotonic Growth)."""
        # Seed 3 days of increasing cases: 5 -> 10 -> 15
        base = timezone.now() - timedelta(days=3)
        for d in range(3):
            count = (d + 1) * 5
            for i in range(count):
                Appointment.objects.create(
                    appointment_datetime=base + timedelta(days=d),
                    disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
                    op_number=f"OUT-{d}-{i}"
                )
        
        # Test detection logic
        from analytics.services.spike_detection import SpikeDetectionService
        service = SpikeDetectionService()
        outbreaks = service.detect_early_outbreaks(min_days=3)
        self.assertTrue(len(outbreaks) > 0)
        self.assertEqual(outbreaks[0]['disease_name'], 'Seasonal Flu')


    def test_stock_depletion_forecast(self):
        """Feature 4: Test Intelligent Stock Depletion Forecast."""
        drug = DrugMaster.objects.create(drug_name="Amox", current_stock=100, clinic=self.clinic)
        
        # Seed usage: 10 units per day
        for i in range(5):
             appt = Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=i),
                disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
                op_number=f"RX-{i}"
            )
             rx = Prescription.objects.create(prescription_date=date.today()-timedelta(days=i), appointment=appt, clinic=self.clinic, doctor=self.doctor, patient=self.patient)
             PrescriptionLine.objects.create(prescription=rx, drug=drug, quantity=10, disease=self.disease)
        
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.admin
        
        res = self.service.forecast_stock_depletion("Amox", days=7, request=request)
        # Factor in growth (approx 42% in test data)
        # 100 stock / (10 avg * 1.42 growth) = approx 7.0 days
        self.assertAlmostEqual(res['days_until_depletion'], 7.0, delta=1)

        self.assertEqual(res['status'], 'low') # 10 < 14
