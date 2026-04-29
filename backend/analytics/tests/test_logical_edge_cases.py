from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from django.utils import timezone
from datetime import date, timedelta

class LogicalEdgeCaseTestCase(APITestCase):
    """
    Advanced logical audit tests. 
    These tests target the 'silent' failures that cause 500 errors in the browser.
    """

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Alpha", clinic_address_1="Central")
        self.user_admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        UserProfile.objects.create(user=self.user_admin, role="ADMIN")
        self.client.force_authenticate(user=self.user_admin)

    def test_api_with_zero_appointments(self):
        """
        LOGICAL AUDIT 1: Zero Data Scenario.
        The system must not crash if no appointments exist.
        """
        urls = [
            reverse('dashboard-stats'),
            reverse('disease-trends'),
            reverse('disease-timeseries'),
            reverse('spike-alerts'),
            reverse('restock-suggestions'),
            reverse('platform-dashboard'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, status.HTTP_200_OK, 
                f"Endpoint {url} crashed with 500 on empty database."
            )

    def test_invalid_query_params_handling(self):
        """
        LOGICAL AUDIT 2: Malformed Parameters.
        Passing empty strings or non-integers to endpoints that expect numbers.
        """
        url = reverse('disease-trends')
        # Empty string for 'days'
        response = self.client.get(url, {'days': ''})
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST],
            "Endpoint crashed on empty string parameter."
        )

    def test_missing_profile_crash(self):
        """
        LOGICAL AUDIT 3: Missing User Profile.
        If a user is authenticated but has no UserProfile record.
        """
        user_no_profile = User.objects.create_user(username="noprofile", password="pw")
        self.client.force_authenticate(user=user_no_profile)
        
        url = reverse('dashboard-stats')
        response = self.client.get(url)
        # Should return 403 or 200 (filtered to empty), NOT 500.
        self.assertNotEqual(response.status_code, 500, "System crashed for user without a profile.")

    def test_disease_with_null_fields(self):
        """
        LOGICAL AUDIT 4: Incomplete Data Records.
        If a disease exists but has null values for critical analytical fields.
        """
        bad_disease = Disease.objects.create(name="Ghost Disease", season=None) # season is None
        doctor = Doctor.objects.create(first_name="Dr", clinic=self.clinic, gender="M", qualification="MD")
        patient = Patient.objects.create(first_name="P", last_name="L", clinic=self.clinic, gender="M", dob="1990-01-01")
        
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=bad_disease,
            clinic=self.clinic,
            doctor=doctor,
            patient=patient,
            op_number="BAD-1"
        )
        
        url = reverse('disease-trends')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Crashed when encountering a disease with null season.")

    def test_extreme_date_range(self):
        """
        LOGICAL AUDIT 5: Future Data.
        What if appointments are accidentally logged with future dates?
        """
        doctor = Doctor.objects.create(first_name="Dr", clinic=self.clinic, gender="M", qualification="MD")
        patient = Patient.objects.create(first_name="P", last_name="L", clinic=self.clinic, gender="M", dob="1990-01-01")
        disease = Disease.objects.create(name="FutureFlu")
        
        # Appointment 1 year in the future
        Appointment.objects.create(
            appointment_datetime=timezone.now() + timedelta(days=365),
            disease=disease,
            clinic=self.clinic,
            doctor=doctor,
            patient=patient,
            op_number="FUT-1"
        )
        
        url = reverse('dashboard-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Crashed when encountering future-dated appointments.")
