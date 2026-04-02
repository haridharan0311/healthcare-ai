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
    
    def test_today_summary_endpoint(self):
        """Test that today summary endpoint returns data."""
        response = self.client.get('/api/today-summary/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_today', data)


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
