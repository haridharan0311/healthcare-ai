from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment

class RBACIsolationTestCase(APITestCase):
    """Integration tests for Multi-clinic RBAC and Data Isolation."""

    def setUp(self):
        # 1. Main Clinic
        self.clinic_main = Clinic.objects.create(clinic_name="Main Clinic")
        self.user_main = User.objects.create_user(username="staff_main", password="pw")
        UserProfile.objects.create(user=self.user_main, role="CLINIC_USER", clinic=self.clinic_main)
        
        # 2. Remote Clinic
        self.clinic_remote = Clinic.objects.create(clinic_name="Remote Clinic")
        self.user_remote = User.objects.create_user(username="staff_remote", password="pw")
        UserProfile.objects.create(user=self.user_remote, role="CLINIC_USER", clinic=self.clinic_remote)
        
        self.disease = Disease.objects.create(name="Fever", season="ALL")
        self.doctor = Doctor.objects.create(first_name="DrI", clinic=self.clinic_main)
        self.patient = Patient.objects.create(first_name="PatI", dob="1990-01-01", clinic=self.clinic_main)

    def test_clinic_data_isolation(self):
        """Verify that clinic user only sees their own clinic's data."""
        # Seed data for Main Clinic
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic_main, doctor=self.doctor, patient=self.patient,
            op_number="MAIN-1"
        )
        
        # Seed data for Remote Clinic with unique disease name
        d_remote = Disease.objects.create(name="RemoteExclusive", season="ALL")
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=d_remote, clinic=self.clinic_remote, doctor=self.doctor, patient=self.patient,
            op_number="REMOTE-1"
        )
        
        url = reverse('disease-trends')
        
        # 1. Main User should see MAIN-1 but NOT REMOTE-1
        self.client.force_authenticate(user=self.user_main)
        res_main = self.client.get(url)
        self.assertIn("Fever", str(res_main.data))
        self.assertNotIn("RemoteExclusive", str(res_main.data))
        
        # 2. Remote User should see REMOTE-1 but NOT MAIN-1
        self.client.force_authenticate(user=self.user_remote)
        res_remote = self.client.get(url)
        self.assertIn("RemoteExclusive", str(res_remote.data))
        self.assertNotIn("Fever", str(res_remote.data))

    def test_cache_isolation_per_user(self):
        """Verify that cached responses are unique to each user's clinic context."""
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic_main, doctor=self.doctor, patient=self.patient,
            op_number="CACHE-1"
        )
        
        url = reverse('disease-trends')
        
        # 1. User Main hits the API (populates cache for their ID)
        self.client.force_authenticate(user=self.user_main)
        self.client.get(url)
        
        # 2. User Remote hits the same URL
        self.client.force_authenticate(user=self.user_remote)
        response = self.client.get(url)
        
        # Should NOT see Main clinic data (Fever) because cache key includes User ID
        self.assertNotIn("Fever", str(response.data))
