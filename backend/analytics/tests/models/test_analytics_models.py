from django.test import TestCase
from django.utils import timezone
from analytics.models import Disease, Appointment
from core.models import Clinic, Doctor, Patient

class AnalyticsModelsTestCase(TestCase):
    """Tests for models in the analytics app."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Test Clinic")
        self.disease = Disease.objects.create(name="Flu", season="Winter", severity=2)
        self.doctor = Doctor.objects.create(first_name="Dr. Smith", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="John", gender="M", dob="1990-01-01", clinic=self.clinic)

    def test_appointment_integrity(self):
        """Test creation and relationship linking for Appointment."""
        appt = Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
            op_number="OP123"
        )
        self.assertEqual(appt.disease.name, "Flu")
        self.assertEqual(appt.clinic.clinic_name, "Test Clinic")

    def test_disease_defaults(self):
        """Test default values of Disease model."""
        d = Disease.objects.create(name="New Disease")
        self.assertTrue(d.is_active)
        self.assertEqual(d.severity, 1)

    def test_on_delete_cascade_protection(self):
        """Test that appointments are removed when the linked clinic is deleted."""
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
            op_number="OP-DEL"
        )
        self.clinic.delete()
        self.assertEqual(Appointment.objects.count(), 0)
