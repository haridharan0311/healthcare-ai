"""
Tests for Analytics API Endpoints
==================================
Tests for disease trends, spike alerts, restock suggestions, and other API views.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from datetime import datetime, timedelta

from core.models import Clinic, Doctor, Patient
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.models import Disease, Appointment
from django.utils import timezone


class DiseaseAnalyticsAPITestCase(TestCase):
    """Test disease analytics endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.clinic = Clinic.objects.create(
            clinic_name="Test Clinic",
            clinic_address_1="123 Main St"
        )
        
        cls.disease = Disease.objects.create(
            name="Test Disease",
            season="All",
            category="Test",
            severity=1,
            is_active=True,
            created_at=timezone.now()
        )
        
        cls.doctor = Doctor.objects.create(
            first_name="John",
            last_name="Doe",
            gender="M",
            qualification="MD",
            clinic=cls.clinic
        )
        
        cls.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Doe",
            gender="F",
            title="Ms",
            dob="1990-01-01",
            mobile_number="9876543210",
            address_line_1="456 Oak Ave",
            clinic=cls.clinic
        )
        
        # Create appointment
        cls.appointment = Appointment.objects.create(
            appointment_datetime=timezone.now(),
            appointment_status="Completed",
            disease=cls.disease,
            clinic=cls.clinic,
            doctor=cls.doctor,
            patient=cls.patient,
            op_number="OP000001"
        )
    
    def setUp(self):
        """Set up for each test."""
        self.client = APIClient()
    
    def test_disease_trends_endpoint(self):
        """Test that disease trends endpoint returns data."""
        response = self.client.get('/api/disease-trends/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # print("Disease Trends Data:", data)  # Debug print
        if data:
            self.assertIn('disease_name', data[0])
    
    def test_spike_alerts_endpoint(self):
        """Test that spike alerts endpoint returns data."""
        response = self.client.get('/api/spike-alerts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if data:
            self.assertIn('disease_name', data[0])
    
    def test_medicine_usage_endpoint(self):
        """Test medicine usage endpoint returns data."""
        response = self.client.get('/api/medicine-usage/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_trend_comparison_endpoint(self):
        """Test trend comparison endpoint returns data."""
        response = self.client.get('/api/trend-comparison/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('results', data)


class RestockAnalyticsAPITestCase(TestCase):
    """Test restock suggestion endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.clinic = Clinic.objects.create(
            clinic_name="Test Clinic",
            clinic_address_1="123 Main St"
        )
        
        cls.drug = DrugMaster.objects.create(
            drug_name="Aspirin",
            generic_name="Acetylsalicylic acid",
            drug_strength="500mg",
            dosage_type="Tablet",
            clinic=cls.clinic,
            current_stock=100
        )
    
    def setUp(self):
        """Set up for each test."""
        self.client = APIClient()
    
    def test_low_stock_alerts_endpoint(self):
        """Test that low stock alerts endpoint returns data."""
        response = self.client.get('/api/low-stock-alerts/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)
    
    def test_district_restock_endpoint(self):
        """Test that district restock endpoint returns data."""
        response = self.client.get('/api/district-restock/?district=Test&days=30')
        # Should either return 200 or 404 (if district doesn't exist)
        self.assertIn(response.status_code, [200, 404])


class AnalyticsCoverageAPITestCase(TestCase):
    """Extended coverage for new API endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.clinic = Clinic.objects.create(clinic_name='Test Clinic', clinic_address_1='123 Main St')
        cls.disease = Disease.objects.create(name='Flu', season='Winter', category='Respiratory', severity=2, is_active=True, created_at=timezone.now())
        cls.doctor = Doctor.objects.create(first_name='Alice', last_name='Smith', gender='F', qualification='MD', clinic=cls.clinic)
        cls.patient = Patient.objects.create(first_name='Bob', last_name='Jones', gender='M', title='Mr', dob='1985-09-21', mobile_number='9998887776', address_line_1='789 Pine St', clinic=cls.clinic)
        cls.appointment = Appointment.objects.create(appointment_datetime=timezone.now(), appointment_status='Completed', disease=cls.disease, clinic=cls.clinic, doctor=cls.doctor, patient=cls.patient, op_number='OP000002')

        cls.drug = DrugMaster.objects.create(drug_name='Paracetamol', generic_name='Acetaminophen', drug_strength='500mg', dosage_type='Tablet', clinic=cls.clinic, current_stock=30)
        cls.prescription = Prescription.objects.create(prescription_date=timezone.now().date(), appointment=cls.appointment, clinic=cls.clinic, doctor=cls.doctor, patient=cls.patient)
        PrescriptionLine.objects.create(duration='5 days', instructions='Twice daily', prescription=cls.prescription, disease=cls.disease, quantity=20, drug=cls.drug)

    def setUp(self):
        self.client = APIClient()

    def test_top_medicines_endpoint(self):
        response = self.client.get('/api/top-medicines/?days=30&limit=5')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('top_medicines', data)
        self.assertIsInstance(data['top_medicines'], list)
        self.assertTrue(len(data['top_medicines']) >= 1)
        self.assertIn('drug_name', data['top_medicines'][0])

    def test_seasonality_endpoint(self):
        response = self.client.get('/api/seasonality/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('seasons', data)
        self.assertIn('Winter', data['seasons'])

    def test_doctor_trends_endpoint(self):
        response = self.client.get('/api/doctor-trends/?days=30&limit=10')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('data', data)
        if data['data']:
            self.assertIn('doctor_name', data['data'][0])

    def test_weekly_report_endpoint(self):
        response = self.client.get('/api/reports/weekly/?days=90')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('weeks', data)

    def test_monthly_report_endpoint(self):
        response = self.client.get('/api/reports/monthly/?days=365')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('months', data)

    def test_what_changed_today_endpoint(self):
        response = self.client.get('/api/what-changed-today/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('date', data)
        self.assertIn('stock_risks', data)
        self.assertIn('spike_alerts', data)

    def test_medicine_dependency_endpoint(self):
        response = self.client.get('/api/medicine-dependency/?days=30&disease=Flu')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, dict) or isinstance(data, list))

    def test_stock_depletion_forecast_endpoint(self):
        response = self.client.get(f'/api/stock-depletion/?drug_id={self.drug.id}&days=30&forecast_days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('drug_name', data)
        self.assertIn('days_until_depletion', data)

    def test_adaptive_buffer_endpoint(self):
        response = self.client.get('/api/adaptive-buffer/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('adaptive_buffer', data)

    def test_trend_comparison_with_data(self):
        response = self.client.get('/api/trend-comparison/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('results', data)

    def test_all_analytics_endpoints_coverage(self):
        """Comprehensive coverage for each analytics API scenario."""
        checks = [
            ('/api/disease-trends/?days=30', list, None),
            ('/api/disease-trends/timeseries/?days=30', list, None),
            ('/api/medicine-usage/?days=30', list, None),
            ('/api/spike-alerts/?days=30&all=true', list, None),
            ('/api/restock-suggestions/?days=30', list, None),
            ('/api/district-restock/?days=30', dict, ['districts', 'total']),
            ('/api/trend-comparison/?days=30', dict, ['results', 'summary']),
            ('/api/top-medicines/?days=30&limit=10', dict, ['top_medicines']),
            ('/api/low-stock-alerts/?threshold=50', dict, ['out_of_stock', 'alerts']),
            ('/api/seasonality/?days=365', dict, ['seasons']),
            ('/api/doctor-trends/?days=30&min_cases=0', dict, ['data']),
            ('/api/reports/weekly/?days=90', dict, ['weeks']),
            ('/api/reports/monthly/?days=365', dict, ['months']),
            ('/api/today-summary/', dict, ['total_today']),
        ]

        for path, expected_type, required_keys in checks:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, f'Endpoint failed: {path}')
            data = response.json()
            self.assertIsInstance(data, expected_type, f'{path} returned {type(data)}')
            if required_keys:
                for key in required_keys:
                    self.assertIn(key, data, f'{path} missing {key}')

        season_data = self.client.get('/api/seasonality/?days=365').json()
        if season_data.get('seasons'):
            for season_value in season_data.get('seasons').values():
                self.assertGreaterEqual(season_value.get('total_cases', 0), 0)

        doctor_data = self.client.get('/api/doctor-trends/?days=30&min_cases=0').json()
        self.assertIn('data', doctor_data)

    def test_low_stock_alerts_threshold(self):
        response = self.client.get('/api/low-stock-alerts/?threshold=50')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('out_of_stock', data)

    def test_platform_dashboard_endpoint(self):
        """Tiered Architecture Dashboard test."""
        response = self.client.get('/api/insights/platform-dashboard/?days=30&forecast_days=7')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('health_analytics', data['data'])
        self.assertIn('insights', data['data'])

    def test_insights_summary_endpoint(self):
        """Decision Layer Summary test."""
        response = self.client.get('/api/insights/summary/?days=30')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('insights', data)
        self.assertIn('recommendations', data['insights'])

    def test_unified_alerts_endpoint(self):
        """Unified Alert Stream test."""
        response = self.client.get('/api/insights/alerts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('alerts', data)
        self.assertIsInstance(data['alerts'], list)

    def test_intelligent_report_export(self):
        """Intelligent Reporting System CSV test."""
        response = self.client.get('/api/export-report/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('DECISION SUPPORT SUMMARY', content)
        self.assertIn('STRATEGIC RECOMMENDATIONS', content)

    def test_api_parameters_days_validation(self):
        """Test with different 'days' parameters."""
        test_days = [1, 7, 30, 90]
        for d in test_days:
            response = self.client.get(f'/api/disease-trends/?days={d}')
            self.assertEqual(response.status_code, 200, f"Failed for days={d}")

    def test_api_parameters_invalid_days(self):
        """Test with invalid 'days' parameter."""
        # The view should handle error gracefully or use default
        response = self.client.get('/api/disease-trends/?days=invalid')
        # Based on my previous view check, it uses a default if ValueError occurs
        self.assertEqual(response.status_code, 200)

