import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster
from django.utils import timezone
from datetime import date, timedelta

class AnalyticsAPITestCase(APITestCase):
    """
    Exhaustive test suite for Analytics API endpoints.
    Covers core data retrieval, parameter validation, and RBAC security.
    """

    def setUp(self):
        # ── Setup Models ──
        self.clinic = Clinic.objects.create(clinic_name="Main", clinic_address_1="City")
        self.user_admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        self.user_clinic = User.objects.create_user(username="user1", password="pw")
        
        UserProfile.objects.create(user=self.user_admin, role="ADMIN")
        UserProfile.objects.create(user=self.user_clinic, role="CLINIC_USER", clinic=self.clinic)

        self.disease = Disease.objects.create(name="Fever", season="ALL", created_at=timezone.now())
        self.doctor = Doctor.objects.create(first_name="Dr", clinic=self.clinic, gender="M", qualification="MD")
        self.patient = Patient.objects.create(first_name="P", last_name="L", clinic=self.clinic, gender="M", dob="1990-01-01")
        
        # Seed some data
        Appointment.objects.create(
            appointment_datetime=timezone.now(), appointment_status="C",
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number="X1"
        )

    def test_unauthorized_access(self):
        url = reverse('disease-trends')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Core Analytics Endpoints ────────────────────────────────────

    def test_disease_trends_api(self):
        """Test disease trends retrieval."""
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('disease-trends')
        response = self.client.get(url, {'days': 30})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Fever', str(response.data))

    def test_timeseries_api(self):
        """Test time-series data structure."""
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('disease-timeseries')
        response = self.client.get(url, {'days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Timeseries returns a list of daily data points
        self.assertIsInstance(response.data, list)
        self.assertIn('case_count', response.data[0])

    # ── Spike Detection Endpoints ───────────────────────────────────

    def test_spike_alerts_api(self):
        """Test spike detection endpoint."""
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('spike-alerts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    # ── Restock & Inventory Endpoints ────────────────────────────────

    def test_restock_suggestions_api(self):
        """Test replenishment recommendation logic."""
        DrugMaster.objects.create(drug_name="DrugA", current_stock=5, clinic=self.clinic)
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('restock-suggestions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Unified Dashboard Endpoints ─────────────────────────────────

    def test_platform_dashboard_api(self):
        """Test the mega-dashboard stats endpoint."""
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('platform-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Unified dashboard wraps data in a 'data' key
        self.assertIn('health_analytics', response.data['data'])

    # ── Role Based Access Control (RBAC) ────────────────────────────

    def test_clinic_user_isolation(self):
        """Verify that CLINIC_USER only gets data for their own clinic."""
        other_clinic = Clinic.objects.create(clinic_name="Other", clinic_address_1="Other")
        Disease.objects.create(name="RemoteDisease", season="ALL", created_at=timezone.now())
        # Appointment for OTHER clinic
        Appointment.objects.create(
            appointment_datetime=timezone.now(), appointment_status="C",
            disease=Disease.objects.get(name="RemoteDisease"), clinic=other_clinic, 
            doctor=Doctor.objects.create(first_name="Dr2", clinic=other_clinic, gender="M", qualification="MD"), 
            patient=Patient.objects.create(first_name="P2", last_name="L2", clinic=other_clinic, gender="M", dob="1990-01-01"), op_number="Y2"
        )

        self.client.force_authenticate(user=self.user_clinic) # Clinic user for 'Main'
        url = reverse('disease-trends')
        response = self.client.get(url)
        
        # Should contain Fever (Main) but NOT RemoteDisease (Other)
        res_str = str(response.data)
        self.assertIn('Fever', res_str)
        self.assertNotIn('RemoteDisease', res_str)

    # ── Edge Case: Invalid Parameters ───────────────────────────────

    def test_invalid_days_parameter(self):
        """Verify handling of invalid query parameters."""
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('disease-trends')
        response = self.client.get(url, {'days': -5}) # Negative days
        # Based on implementation, should either default or return error. 
        # Most views default to a safe value (30).
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Simulator Endpoints ─────────────────────────────────────────

    def test_simulator_toggle(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('simulator-toggle')
        response = self.client.post(url, {'action': 'start', 'interval': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['running'])
