from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User
from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from analytics.services.usage import UsageIntelligence

class DoctorPerformanceTestCase(TestCase):
    """Feature 7: Doctor-wise Performance Analytics tests."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Doc Clinic")
        self.user = User.objects.create_user(username="doc_staff", password="pw")
        UserProfile.objects.create(user=self.user, role="CLINIC_USER", clinic=self.clinic)
        self.disease = Disease.objects.create(name="Malaria")
        self.doc = Doctor.objects.create(first_name="DrP", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatP", dob="2000-01-01", clinic=self.clinic)

    def test_doctor_efficiency_score(self):
        # 10 cases
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=timezone.now(),
                disease=self.disease, clinic=self.clinic, doctor=self.doc, patient=self.pat,
                op_number=f"P-{i}"
            )
        
        from analytics.views.utils import apply_clinic_filter
        intel = UsageIntelligence()
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user
        qs = apply_clinic_filter(Appointment.objects.all(), request)
        
        res = intel.get_doctor_patterns(days=30, appt_queryset=qs)
        self.assertEqual(res[0]['total_cases'], 10)
        self.assertGreater(res[0]['efficiency_score'], 0)

