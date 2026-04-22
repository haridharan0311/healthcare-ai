import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment

class AnalyticsAPITestCase(APITestCase):
    """Tests for API endpoints in the analytics app."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="API Clinic")
        self.user = User.objects.create_user(username="api_staff", password="pw")
        UserProfile.objects.create(user=self.user, role="CLINIC_USER", clinic=self.clinic)
        
        self.disease = Disease.objects.create(name="Fever", season="ALL")
        self.doctor = Doctor.objects.create(first_name="DrV", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="PatV", dob="1990-01-01", clinic=self.clinic)
        
        # Seed data
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
            op_number="API-1"
        )
        self.client.force_authenticate(user=self.user)

    def test_disease_trends_api(self):
        url = reverse('disease-trends')
        response = self.client.get(url, {'days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Fever", str(response.data))

    def test_what_changed_today_api(self):
        url = reverse('what-changed-today')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_appointments'], 1)


    def test_doctor_trends_api(self):
        url = reverse('doctor-trends')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['data']), 0)

    def test_invalid_parameters_fallback(self):
        url = reverse('disease-trends')
        response = self.client.get(url, {'days': 'invalid_string'})
        # Should fallback to default days (30) and return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
