from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User
from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from analytics.services.dashboard_service import DashboardService

class DashboardServiceTestCase(TestCase):
    """Features 9 & 10: Multi-Level Analytics & What Changed Today."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Dash Clinic")
        self.user = User.objects.create_user(username="dash_staff", password="pw")
        UserProfile.objects.create(user=self.user, role="CLINIC_USER", clinic=self.clinic)
        self.disease = Disease.objects.create(name="Flu")
        self.doc = Doctor.objects.create(first_name="DrD", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatD", dob="2000-01-01", clinic=self.clinic)

    def test_what_changed_today_summary(self):
        # 1 appointment today
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic, doctor=self.doc, patient=self.pat,
            op_number="D-1"
        )
        
        service = DashboardService()
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        # DashboardService.get_stats_fragment is the correct method for top-level stats
        res = service.get_stats_fragment(days=1, request=request)
        self.assertEqual(res['total_appointments'], 1)
        self.assertIn("risk_status", res)
