from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic, Doctor, Patient
from analytics.services.timeseries import TimeSeriesAnalysis
from analytics.services.spike_detection import SpikeDetectionService
from analytics.services.restock_calculator import calculate_dynamic_safety_buffer
from analytics.services.usage import UsageIntelligence
from analytics.services.forecasting import ForecastingService
from analytics.services.alert_engine import AlertEngineService
from analytics.services.insights_service import InsightsService
from analytics.services.dashboard_service import DashboardService

class AdvancedFeaturesTestCase(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Test Clinic", clinic_address_1="Test Address")
        self.doctor = Doctor.objects.create(
            first_name="Dr. Smith", 
            gender="M", 
            qualification="MD", 
            clinic=self.clinic
        )
        self.patient = Patient.objects.create(
            first_name="John", 
            last_name="Doe", 
            gender="M", 
            title="Mr", 
            dob="1990-01-01", 
            mobile_number="1234567890", 
            address_line_1="Addr 1", 
            clinic=self.clinic
        )
        self.disease = Disease.objects.create(
            name="Seasonal Flu", 
            season="Winter", 
            severity=2, 
            created_at=timezone.now()
        )
        self.drug = DrugMaster.objects.create(drug_name="FluMed", current_stock=100, clinic=self.clinic)

    def test_feature_1_growth_rate(self):
        """Test Disease Growth Rate Indicator."""
        ts = TimeSeriesAnalysis()
        # Seed data: 5 cases last week, 10 cases this week (100% growth)
        for i in range(5):
            Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=10), 
                disease=self.disease, 
                clinic=self.clinic,
                doctor=self.doctor,
                patient=self.patient,
                op_number=f"G1-{i}"
            )
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=2), 
                disease=self.disease, 
                clinic=self.clinic,
                doctor=self.doctor,
                patient=self.patient,
                op_number=f"G2-{i}"
            )
        
        res = ts.calculate_growth_rate("Seasonal Flu", days=7)
        self.assertEqual(res['growth_rate'], 100.0)
        self.assertEqual(res['status'], 'rising')
        self.assertEqual(res['direction'], 'up')

    def test_feature_2_early_outbreak(self):
        """Test Early Outbreak Detection (Monotonic Growth)."""
        service = SpikeDetectionService()
        # Seed 4 days of strictly increasing cases: 2, 4, 6, 8
        base_date = timezone.now() - timedelta(days=4)
        for d in range(4):
            count = (d + 1) * 2
            for i in range(count):
                Appointment.objects.create(
                    appointment_datetime=base_date + timedelta(days=d),
                    disease=self.disease,
                    clinic=self.clinic,
                    doctor=self.doctor,
                    patient=self.patient,
                    op_number=f"OB-{d}-{i}"
                )
        
        outbreaks = service.detect_early_outbreaks(min_days=3, min_cases=1)
        self.assertTrue(any(o['disease_name'] == 'Seasonal Flu' for o in outbreaks))
        flu_alert = next(o for o in outbreaks if o['disease_name'] == 'Seasonal Flu')
        self.assertGreater(flu_alert['impact_score'], 50)

    def test_feature_5_adaptive_buffer(self):
        """Test Adaptive Safety Buffer with Volatility."""
        # Scenario 1: Low volatility, no spikes
        buffer_low = calculate_dynamic_safety_buffer(spike_count=0, total_diseases=10, volatility=0.1)
        # Scenario 2: High volatility + spikes
        buffer_high = calculate_dynamic_safety_buffer(spike_count=5, total_diseases=10, volatility=0.8)
        
        self.assertGreater(buffer_high, buffer_low)
        self.assertGreaterEqual(buffer_high, 1.2) # Base is 1.2

    def test_feature_6_seasonal_learning(self):
        """Test Seasonal Pattern Learning (Shift Detection)."""
        ts = TimeSeriesAnalysis()
        # Create two versions of the same disease with different historical seasons
        # Version 1: Winter (Historical)
        # Version 2: Summer (Current Activity)
        # Querying "ShiftedFlu" should find Version 1's season as historical, 
        # but find Version 2's cases in current distribution.
        Disease.objects.create(name="ShiftedFlu V1", season="Winter", created_at=timezone.now())
        v2 = Disease.objects.create(name="ShiftedFlu V2", season="Summer", created_at=timezone.now())
        
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=timezone.now(), 
                disease=v2, 
                clinic=self.clinic,
                doctor=self.doctor,
                patient=self.patient,
                op_number=f"S-{i}"
            )
        
        res = ts.get_seasonal_patterns("ShiftedFlu")
        self.assertEqual(res['historical_peak_season'], "Winter")
        self.assertEqual(res['current_peak_season'], "Summer")
        self.assertTrue(res['pattern_shift_detected'])
        self.assertEqual(res['status'], 'pattern_shifted')

    def test_feature_7_doctor_performance(self):
        """Test Doctor-wise Performance Analytics."""
        usage = UsageIntelligence()
        # Seed doctor data
        for i in range(15):
            Appointment.objects.create(
                appointment_datetime=timezone.now(), 
                disease=self.disease, 
                doctor=self.doctor, 
                clinic=self.clinic,
                patient=self.patient,
                op_number=f"D-{i}"
            )
        
        res = usage.get_doctor_patterns(doctor_id=self.doctor.id, days=30)
        self.assertEqual(res['total_cases'], 15)
        self.assertGreater(res['cases_per_day'], 0)

    def test_feature_4_stock_depletion(self):
        """Test Intelligent Stock Depletion Forecast."""
        forecast = ForecastingService()
        # Seed usage
        appt = Appointment.objects.create(
            appointment_datetime=timezone.now(), 
            disease=self.disease, 
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
            op_number="STK-1"
        )
        rx = Prescription.objects.create(
            prescription_date=date.today(), 
            appointment=appt, 
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient
        )
        PrescriptionLine.objects.create(prescription=rx, drug=self.drug, quantity=20, disease=self.disease)
        
        # Current stock 100, usage 20 today. Avg daily ~20.
        # If disease is growing, depletion should be faster.
        # Add growth
        for i in range(5):
            Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=7), 
                disease=self.disease, 
                clinic=self.clinic,
                doctor=self.doctor,
                patient=self.patient,
                op_number=f"STK-G1-{i}"
            )
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=1), 
                disease=self.disease, 
                clinic=self.clinic,
                doctor=self.doctor,
                patient=self.patient,
                op_number=f"STK-G2-{i}"
            )
        
        res = forecast.forecast_stock_depletion("FluMed", days=7)
        self.assertIn('predicted_daily_usage', res)
        self.assertGreater(res['predicted_daily_usage'], res['avg_daily_usage'])

    def test_feature_8_alert_engine(self):
        """Test Unified Alert Engine."""
        engine = AlertEngineService()
        # Trigger an outbreak
        for i in range(5):
            count = (i + 1) * 5
            for j in range(count):
                Appointment.objects.create(
                    appointment_datetime=timezone.now() - timedelta(days=5-i),
                    disease=self.disease,
                    clinic=self.clinic,
                    doctor=self.doctor,
                    patient=self.patient,
                    op_number=f"AE-{i}-{j}"
                )
        
        alerts = engine.get_unified_alerts(days=7)
        self.assertGreater(len(alerts), 0)
        self.assertEqual(alerts[0]['type'], 'outbreak')

    def test_feature_9_multi_level_dashboard(self):
        """Test Multi-Level Analytics Dashboard."""
        dash = DashboardService()
        res = dash.get_unified_dashboard(days=30)
        self.assertIn('multi_level', res)
        self.assertIn('doctor_level', res['multi_level'])
        self.assertIn('clinic_level', res['multi_level'])

    # ── Expanded Feature 1: Growth Rate Variations ──────────────────

    def test_growth_rate_edge_cases(self):
        """Test Growth Rate with zero cases, new diseases, and negative trends."""
        ts = TimeSeriesAnalysis()
        
        # 1. New Disease (Zero previous, some recent)
        d_new = Disease.objects.create(name="New Virus", season="ALL", created_at=timezone.now())
        Appointment.objects.create(
            appointment_datetime=timezone.now(), 
            disease=d_new, 
            clinic=self.clinic, 
            doctor=self.doctor, 
            patient=self.patient, 
            op_number="NV-1"
        )
        res_new = ts.calculate_growth_rate("New Virus", days=7)
        self.assertEqual(res_new['status'], 'new')
        self.assertEqual(res_new['growth_rate'], 100.0)
        
        # 2. Stable / No Change
        d_stable = Disease.objects.create(name="StableCold", season="ALL", created_at=timezone.now())
        for i in range(5):
            Appointment.objects.create(appointment_datetime=timezone.now() - timedelta(days=10), disease=d_stable, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number=f"S1-{i}")
            Appointment.objects.create(appointment_datetime=timezone.now() - timedelta(days=2), disease=d_stable, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number=f"S2-{i}")
        res_stable = ts.calculate_growth_rate("StableCold", days=7)
        self.assertEqual(res_stable['growth_rate'], 0.0)
        self.assertEqual(res_stable['status'], 'stable')

        # 3. Negative Trend
        d_fade = Disease.objects.create(name="FadingFlu", season="ALL", created_at=timezone.now())
        for i in range(10):
            Appointment.objects.create(appointment_datetime=timezone.now() - timedelta(days=10), disease=d_fade, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number=f"F1-{i}")
        for i in range(2):
            Appointment.objects.create(appointment_datetime=timezone.now() - timedelta(days=2), disease=d_fade, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number=f"F2-{i}")
        res_negative = ts.calculate_growth_rate("FadingFlu", days=7)
        self.assertLess(res_negative['growth_rate'], 0)
        self.assertEqual(res_negative['direction'], 'down')

    # ── Expanded Feature 2: Outbreak Detection Parameters ───────────

    def test_outbreak_parameter_variations(self):
        """Test outbreak detection with different thresholds and non-monotonic trends."""
        service = SpikeDetectionService()
        
        # Scenario: Non-monotonic but high slope (2, 1, 10, 20)
        d_volatile = Disease.objects.create(name="VolatileVirus", season="ALL", created_at=timezone.now())
        counts = [2, 1, 10, 20]
        base_date = timezone.now() - timedelta(days=len(counts))
        for d, count in enumerate(counts):
            for i in range(count):
                Appointment.objects.create(
                    appointment_datetime=base_date + timedelta(days=d),
                    disease=d_volatile, 
                    clinic=self.clinic, 
                    doctor=self.doctor, 
                    patient=self.patient, 
                    op_number=f"V-{d}-{i}"
                )
        
        # Should be detected due to high slope even if not strictly increasing
        outbreaks = service.detect_early_outbreaks(min_days=3, min_cases=5)
        self.assertTrue(any(o['disease_name'] == 'VolatileVirus' for o in outbreaks))

    # ── Expanded Feature 4: Stock Depletion Edge Cases ──────────────

    def test_stock_depletion_edge_cases(self):
        """Test stock depletion with zero stock, zero usage, and high growth."""
        forecast = ForecastingService()
        
        # 1. No usage
        res_no_usage = forecast.forecast_stock_depletion("EmptyMed")
        self.assertEqual(res_no_usage['days_until_depletion'], 999)
        
        # 2. Critical Stock (1 unit left)
        crit_drug = DrugMaster.objects.create(drug_name="CritMed", current_stock=1, clinic=self.clinic)
        # Usage: 10 per day
        appt = Appointment.objects.create(appointment_datetime=timezone.now(), disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number="CM-1")
        rx = Prescription.objects.create(prescription_date=date.today(), appointment=appt, clinic=self.clinic, doctor=self.doctor, patient=self.patient)
        PrescriptionLine.objects.create(prescription=rx, drug=crit_drug, quantity=10, disease=self.disease)
        
        res_crit = forecast.forecast_stock_depletion("CritMed", days=1)
        self.assertLess(res_crit['days_until_depletion'], 1)
        self.assertEqual(res_crit['status'], 'critical')

    # ── Expanded Feature 5: Adaptive Buffer Clamping ───────────────

    def test_adaptive_buffer_boundaries(self):
        """Test buffer clamping and sensitivity to high volatility."""
        # 1. Extremely high volatility should be capped at MAX_SAFETY_BUFFER (1.8)
        buffer_capped = calculate_dynamic_safety_buffer(spike_count=100, total_diseases=1, volatility=10.0)
        self.assertEqual(buffer_capped, 1.8)
        
        # 2. Zero diseases shouldn't crash
        buffer_zero = calculate_dynamic_safety_buffer(spike_count=0, total_diseases=0)
        self.assertEqual(buffer_zero, 1.2)

    # ── Expanded Feature 7: Doctor Summary & Boundaries ─────────────

    def test_doctor_analytics_summary(self):
        """Test doctor-wise analytics for summary view and inactive doctors."""
        usage = UsageIntelligence()
        
        # Seed at least one appointment for summary
        Appointment.objects.create(
            appointment_datetime=timezone.now(), 
            disease=self.disease, 
            doctor=self.doctor, 
            clinic=self.clinic,
            patient=self.patient,
            op_number="D-SUM-1"
        )
        
        # 1. Summary for all doctors
        res_summary = usage.get_doctor_patterns(doctor_id=None, days=30)
        self.assertIsInstance(res_summary, list)
        self.assertGreater(len(res_summary), 0)
        
        # 2. Doctor with no cases
        doc_empty = Doctor.objects.create(first_name="Idle", gender="F", qualification="MD", clinic=self.clinic)
        res_empty = usage.get_doctor_patterns(doctor_id=doc_empty.id, days=30)
        self.assertEqual(res_empty['total_cases'], 0)

    # ── Expanded Feature 8: Alert Priority ──────────────────────────

    def test_alert_engine_prioritization(self):
        """Test that the alert engine correctly ranks critical alerts."""
        from django.contrib.auth.models import User
        from core.models import UserProfile
        from rest_framework.test import APIRequestFactory
        
        # Create an authenticated request for the filter
        user, _ = User.objects.get_or_create(username='alert_admin', email='a@a.com')
        user.is_superuser = True
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={'role': 'ADMIN'})
        
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = user
        
        engine = AlertEngineService()
        
        # Create a "mild growth" alert
        d_mild = Disease.objects.create(name="MildGrowth", season="ALL", created_at=timezone.now())
        for i in range(2): Appointment.objects.create(appointment_datetime=timezone.now() - timedelta(days=10), disease=d_mild, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number=f"M1-{i}")
        for i in range(3): Appointment.objects.create(appointment_datetime=timezone.now() - timedelta(days=2), disease=d_mild, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number=f"M2-{i}")
        
        # Create a "critical stock" alert with usage history
        drug = DrugMaster.objects.create(drug_name="ZeroStock", current_stock=0, clinic=self.clinic)
        # Seed usage so it's not ignored
        from inventory.models import Prescription, PrescriptionLine
        appt = Appointment.objects.create(appointment_datetime=timezone.now(), disease=d_mild, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number="AE-STOCK-1")
        rx = Prescription.objects.create(prescription_date=date.today(), appointment=appt, clinic=self.clinic, doctor=self.doctor, patient=self.patient)
        PrescriptionLine.objects.create(prescription=rx, drug=drug, quantity=5, disease=d_mild)
        
        alerts = engine.get_unified_alerts(days=7, request=request)
        # Critical stock (Score 90) should be higher than mild growth
        self.assertGreater(len(alerts), 0)
        self.assertEqual(alerts[0]['type'], 'stock')

    # ── Expanded Feature 9: Dashboard Fragments ─────────────────────

    def test_dashboard_fragments(self):
        """Test individual dashboard fragments with different time ranges."""
        dash = DashboardService()
        
        # 1. Stats Fragment (30 days vs 90 days)
        stats_30 = dash.get_stats_fragment(days=30)
        stats_90 = dash.get_stats_fragment(days=90)
        self.assertIn('total_appointments', stats_30)
        
        # 2. Trends Fragment
        trends = dash.get_trends_fragment(days=30, forecast_days=14)
        self.assertIn('top_diseases', trends)
        self.assertIn('insights', trends)

    def test_feature_10_what_changed_today(self):
        """Test What Changed Today API."""
        from django.contrib.auth.models import User
        from core.models import UserProfile
        from analytics.views.report_views import WhatChangedTodayView
        from rest_framework.test import APIRequestFactory, force_authenticate
        
        # Use existing user if possible or create one
        user, _ = User.objects.get_or_create(username='admin_test_10', email='t10@t.com')
        user.set_password('p')
        user.is_superuser = True
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={'role': 'ADMIN'})
        
        factory = APIRequestFactory()
        view = WhatChangedTodayView.as_view()
        request = factory.get('/api/what-changed-today/')
        force_authenticate(request, user=user)
        
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.data)
        self.assertIn('risks', response.data)
