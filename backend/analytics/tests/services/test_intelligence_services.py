from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User

from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.services.usage import UsageIntelligence
from analytics.services.insights_service import InsightsService

class IntelligenceServicesTestCase(TestCase):
    """Tests for Intelligence Layer (Features 3, 7, 9, 10)."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Intel Clinic")
        self.user = User.objects.create_user(username="staff_i", password="pw")
        UserProfile.objects.create(user=self.user, role="CLINIC_USER", clinic=self.clinic)
        
        self.disease = Disease.objects.create(name="Fever", season="ALL")
        self.doctor = Doctor.objects.create(first_name="DrI", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="PatI", dob="1990-01-01", clinic=self.clinic)
        self.drug = DrugMaster.objects.create(drug_name="Para", current_stock=100, clinic=self.clinic)

    def test_medicine_usage_intelligence(self):
        """Feature 3: Test Mapping disease to medicine patterns."""
        intel = UsageIntelligence()
        # Seed usage
        appt = Appointment.objects.create(appointment_datetime=timezone.now(), disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number="I-1")
        rx = Prescription.objects.create(prescription_date=date.today(), appointment=appt, clinic=self.clinic, doctor=self.doctor, patient=self.patient)
        PrescriptionLine.objects.create(prescription=rx, drug=self.drug, quantity=2, disease=self.disease)
        
        # Correct method name: get_medicine_usage_per_disease
        res = intel.get_medicine_usage_per_disease(disease_name="Fever")
        patterns = res.get('top_medicines', [])
        self.assertIn("Para", str(patterns))
        self.assertEqual(patterns[0]['total_quantity'], 2)

    def test_doctor_performance_analytics(self):
        """Feature 7: Test Doctor-wise Performance Analytics."""
        intel = UsageIntelligence()
        # Seed 5 cases for this doctor
        for i in range(5):
             Appointment.objects.create(
                appointment_datetime=timezone.now(),
                disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
                op_number=f"DOC-P-{i}"
            )
        
        # Correct parameter: appt_queryset instead of request
        from analytics.views.utils import apply_clinic_filter
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user
        qs = apply_clinic_filter(Appointment.objects.all(), request)
        
        stats = intel.get_doctor_patterns(days=30, appt_queryset=qs)
        self.assertEqual(stats[0]['total_cases'], 5)
        self.assertEqual(stats[0]['doctor_name'], "DrI")

    def test_what_changed_today_logic(self):
        """Feature 10: Test What Changed Today logic via InsightsService."""
        service = InsightsService()
        # Seed today's activity
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
            op_number="WCT-1"
        )
        
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        # InsightsService.get_actionable_insights is the core logic for Feature 10
        res = service.get_actionable_insights(days=1, request=request)
        self.assertIn("recommendations", res)
        self.assertIn("outbreaks", res)
