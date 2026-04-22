import json
from datetime import date, timedelta
from django.urls import reverse, resolve
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.services.timeseries import TimeSeriesAnalysis
from analytics.services.forecasting import ForecastingService
from analytics.services.spike_detection import SpikeDetectionService
from analytics.services.restock_service import RestockService
from analytics.services.alert_engine import AlertEngineService
from analytics.services.usage import UsageIntelligence
from analytics.services.ml_engine import moving_average_forecast, weighted_trend_score, predict_demand
from analytics.utils.live_data_generator import LiveDataGenerator

class ComprehensiveHealthcareTestCase(APITestCase):
    """
    Comprehensive test suite covering all paths, URLs, models, and services.
    Implements full parameter permutation testing.
    """

    @classmethod
    def setUpTestData(cls):
        # 1. Core Infrastructure
        cls.clinic_main = Clinic.objects.create(clinic_name="Main City Clinic", clinic_address_1="Downtown")
        cls.clinic_sub = Clinic.objects.create(clinic_name="Suburb Health", clinic_address_1="North Suburb")
        
        # 2. Users & Roles
        cls.admin_user = User.objects.create_superuser(username="super_admin", email="admin@test.com", password="pw")
        cls.clinic_user = User.objects.create_user(username="clinic_staff", password="pw")
        
        UserProfile.objects.create(user=cls.admin_user, role="ADMIN")
        UserProfile.objects.create(user=cls.clinic_user, role="CLINIC_USER", clinic=cls.clinic_main)

        # 3. Medical Entities
        cls.disease_flu = Disease.objects.create(name="Seasonal Flu", season="Winter", severity=2, created_at=timezone.now())
        cls.disease_malaria = Disease.objects.create(name="Malaria", season="Summer", severity=3, created_at=timezone.now())
        
        cls.doctor_a = Doctor.objects.create(first_name="Alice", gender="F", qualification="MD", clinic=cls.clinic_main)
        cls.doctor_b = Doctor.objects.create(first_name="Bob", gender="M", qualification="MBBS", clinic=cls.clinic_sub)
        
        cls.patient_a = Patient.objects.create(first_name="John", last_name="Doe", gender="M", title="Mr", dob="1985-05-15", mobile_number="1234567890", address_line_1="Addr 1", clinic=cls.clinic_main)
        cls.patient_b = Patient.objects.create(first_name="Jane", last_name="Smith", gender="F", title="Ms", dob="1992-10-20", mobile_number="9876543211", address_line_1="Addr 2", clinic=cls.clinic_sub)

        # 4. Inventory
        cls.drug_a = DrugMaster.objects.create(drug_name="Paracetamol", current_stock=500, clinic=cls.clinic_main)
        cls.drug_b = DrugMaster.objects.create(drug_name="Amoxicillin", current_stock=5, clinic=cls.clinic_main) # Low stock

        # 5. Seed Historical Data (30 days)
        base_date = timezone.now() - timedelta(days=30)
        for i in range(30):
            day = base_date + timedelta(days=i)
            # Create fluctuating trend for Flu
            count = 5 + (i % 5)
            for j in range(count):
                Appointment.objects.create(
                    appointment_datetime=day, 
                    disease=cls.disease_flu, 
                    clinic=cls.clinic_main,
                    doctor=cls.doctor_a,
                    patient=cls.patient_a,
                    op_number=f"FLU-{i}-{j}"
                )

    # ────────────────────────────────────────────────────────────────────────
    # 1. PATHS & URLS TESTS
    # ────────────────────────────────────────────────────────────────────────

    def test_url_resolution(self):
        """Verify that all core URL names resolve to views."""
        core_urls = [
            'disease-trends', 'disease-timeseries', 'medicine-usage',
            'spike-alerts', 'restock-suggestions', 'district-restock',
            'trend-comparison', 'top-medicines', 'low-stock-alerts',
            'seasonality', 'doctor-trends', 'report-weekly', 'report-monthly',
            'today-summary', 'what-changed-today', 'platform-dashboard'
        ]
        for url_name in core_urls:
            url = reverse(url_name)
            self.assertIsNotNone(resolve(url))

    # ────────────────────────────────────────────────────────────────────────
    # 2. PARAMETER PERMUTATION TESTS (API Endpoints)
    # ────────────────────────────────────────────────────────────────────────

    def test_api_parameter_permutations(self):
        """Test API endpoints with multiple combinations of parameters."""
        self.client.force_authenticate(user=self.admin_user)
        
        test_configs = [
            {'url': 'disease-trends', 'params': [
                {'days': 7}, {'days': 90}, {'days': -1},
                {'clinic_id': self.clinic_main.id},
                {'days': 30, 'clinic_id': self.clinic_main.id}
            ]},
            {'url': 'disease-timeseries', 'params': [
                {'days': 14}, {'period': 'MTD'},
                {'disease_name': 'Seasonal Flu'},
                {'days': 30, 'disease_name': 'Seasonal Flu'}
            ]},
            {'url': 'medicine-usage', 'params': [
                {'days': 30}, {'disease': 'Flu'},
                {'generic': 'Paracetamol'},
                {'days': 60, 'disease': 'Flu', 'generic': 'Paracetamol'}
            ]},
            {'url': 'restock-suggestions', 'params': [
                {'days': 7}, {'period': 'WTD'},
                {'clinic_id': self.clinic_main.id}
            ]},
            {'url': 'doctor-trends', 'params': [
                {'days': 30}, {'doctor_id': self.doctor_a.id},
                {'days': 90, 'doctor_id': self.doctor_a.id}
            ]},
        ]

        for config in test_configs:
            url = reverse(config['url'])
            for p in config['params']:
                response = self.client.get(url, p)
                self.assertEqual(response.status_code, status.HTTP_200_OK, f"Failed on {url} with {p}")

    # ────────────────────────────────────────────────────────────────────────
    # 3. RBAC & ISOLATION TESTS
    # ────────────────────────────────────────────────────────────────────────

    def test_clinic_user_data_isolation(self):
        """Verify that clinic users cannot see data from other clinics."""
        # Create an appointment in SUB clinic (Bob)
        Appointment.objects.create(
            appointment_datetime=timezone.now(), 
            disease=self.disease_flu, 
            clinic=self.clinic_sub,
            doctor=self.doctor_b,
            patient=self.patient_b,
            op_number="SUB-ISOLATION-1"
        )
        
        self.client.force_authenticate(user=self.clinic_user) # Clinic User for MAIN
        url = reverse('disease-trends')
        response = self.client.get(url)
        
        # Should only see MAIN clinic data
        self.assertIn('Main City Clinic', str(response.data) if 'clinic' in str(response.data) else 'Seasonal Flu')
        # Suburb Health should NOT be visible
        self.assertNotIn('Suburb Health', str(response.data))

    # ────────────────────────────────────────────────────────────────────────
    # 4. ML ENGINE & MATHEMATICAL ROBUSTNESS
    # ────────────────────────────────────────────────────────────────────────

    def test_ml_engine_boundary_values(self):
        """Test ML functions with edge case inputs."""
        # 1. Moving Average with empty/single data
        self.assertEqual(moving_average_forecast([]), 0.0)
        self.assertEqual(moving_average_forecast([10]), 10.0)
        
        # 2. Trend Score with division by zero avoidance
        score = weighted_trend_score(recent_sum=10, previous_sum=0)
        self.assertEqual(score, 100.0)
        
        # 3. Demand prediction with extreme weights
        demand = predict_demand(trend_score=500.0, forecast_ma=100.0)
        self.assertGreater(demand, 100.0)

    # ────────────────────────────────────────────────────────────────────────
    # 5. SERVICE LAYER CROSS-DEPENDENCIES
    # ────────────────────────────────────────────────────────────────────────

    def test_alert_engine_aggregation_logic(self):
        """Test unified alert engine with multiple overlapping triggers."""
        engine = AlertEngineService()
        
        # 1. Trigger Spike
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=timezone.now(), 
                disease=self.disease_malaria, 
                clinic=self.clinic_main,
                doctor=self.doctor_a,
                patient=self.patient_a,
                op_number=f"SPIKE-{i}"
            )
            
        # 2. Trigger Critical Stock
        # Amoxicillin (drug_b) is already at 5 units (low stock)
        
        # Create a request mock with admin user
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.admin_user
        
        alerts = engine.get_unified_alerts(days=7, request=request)
        
        types = [a['type'] for a in alerts]
        self.assertIn('stock', types)
        # Check that stock is high priority (Score 90)
        stock_alert = next(a for a in alerts if a['type'] == 'stock')
        self.assertEqual(stock_alert['impact_score'], 90.0)

    # ────────────────────────────────────────────────────────────────────────
    # 6. CSV EXPORTS (PATH TESTS)
    # ────────────────────────────────────────────────────────────────────────

    def test_export_endpoints(self):
        """Test that all export endpoints return CSV content."""
        self.client.force_authenticate(user=self.admin_user)
        export_urls = [
            'export-trends', 'export-spikes', 'export-restock', 
            'export-medicine-usage', 'export-doctor-trends'
        ]
        for name in export_urls:
            url = reverse(name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response['Content-Type'], 'text/csv')

    # ────────────────────────────────────────────────────────────────────────
    # 7. CUSTOM COMMANDS & GENERATORS
    # ────────────────────────────────────────────────────────────────────────

    def test_live_data_generator_params(self):
        """Test internal generator logic with varying intensity."""
        gen = LiveDataGenerator()
        # Test baseline generation
        initial_count = Appointment.objects.count()
        gen.generate_data()
        self.assertGreater(Appointment.objects.count(), initial_count)

    # ────────────────────────────────────────────────────────────────────────
    # 8. TODAY'S SNAPSHOT & RISK ANALYSIS
    # ────────────────────────────────────────────────────────────────────────

    def test_today_summary_latest_date(self):
        """Test that today-summary identifies the latest activity correctly."""
        future_date = timezone.now() + timedelta(days=1)
        Appointment.objects.create(
            appointment_datetime=future_date, 
            disease=self.disease_flu, 
            clinic=self.clinic_main,
            doctor=self.doctor_a,
            patient=self.patient_a,
            op_number="FUTURE-1"
        )
        
        url = reverse('today-summary')
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        
        self.assertEqual(response.data['date'], str(future_date.date()))
        self.assertGreaterEqual(response.data['total_today'], 1)

    # ────────────────────────────────────────────────────────────────────────
    # 9. COMPREHENSIVE VIEW PARAMETER TESTS
    # ────────────────────────────────────────────────────────────────────────

    def test_view_parameter_permutations_deep(self):
        """Brute-force test of view parameters to catch unhandled exceptions."""
        self.client.force_authenticate(user=self.admin_user)
        views_to_test = [
            ('disease-trends', ['days', 'disease']),
            ('medicine-usage', ['days', 'disease', 'generic']),
            ('doctor-trends', ['days', 'doctor_id']),
            ('report-weekly', ['days', 'period']),
        ]
        
        for url_name, params in views_to_test:
            url = reverse(url_name)
            # Test empty params
            self.assertEqual(self.client.get(url).status_code, 200)
            # Test invalid types
            self.assertEqual(self.client.get(url, {params[0]: 'invalid'}).status_code, 200)

    # ────────────────────────────────────────────────────────────────────────
    # 10. STOCK DEPLETION FORECAST DEEP DIVE
    # ────────────────────────────────────────────────────────────────────────

    def test_stock_depletion_forecast_logic(self):
        """Test depletion forecasting with increasing demand."""
        service = ForecastingService()
        
        # 1. No stock
        res_zero = service.forecast_stock_depletion("Amoxicillin")
        self.assertEqual(res_zero['status'], 'critical')
        
        # 2. Sufficient stock
        res_suff = service.forecast_stock_depletion("Paracetamol")
        self.assertEqual(res_suff['status'], 'sufficient')
