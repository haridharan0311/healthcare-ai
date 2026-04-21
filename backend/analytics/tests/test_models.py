from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from analytics.models import Disease, Appointment
from core.models import Clinic, Doctor, Patient

class AnalyticsModelsTestCase(TestCase):
    """
    Unit tests for Analytics app database models.
    Ensures data integrity, constraint enforcement, and relationship mapping.
    """

    def setUp(self):
        # Create dependencies
        self.clinic = Clinic.objects.create(
            clinic_name="Alpha Health",
            clinic_address_1="123 Main St"
        )
        self.doctor = Doctor.objects.create(
            first_name="John",
            last_name="Doe",
            gender="M",
            qualification="MBBS",
            clinic=self.clinic
        )
        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            gender="F",
            title="Ms",
            dob="1990-01-01",
            mobile_number="1234567890",
            address_line_1="Home",
            clinic=self.clinic
        )
        self.disease = Disease.objects.create(
            name="Seasonal Flu",
            season="WINTER",
            category="RES",
            severity=3,
            created_at=timezone.now()
        )

    # ── Disease Model Tests ──────────────────────────────────────────

    def test_disease_creation_and_defaults(self):
        """Test default values and active status of Disease model."""
        self.assertEqual(self.disease.name, "Seasonal Flu")
        self.assertTrue(self.disease.is_active)
        self.assertEqual(self.disease.severity, 3)

    def test_disease_string_representation(self):
        """Test the __str__ method of Disease."""
        self.assertEqual(str(self.disease), "Seasonal Flu")

    # ── Appointment Model Tests ──────────────────────────────────────

    def test_appointment_integrity(self):
        """Test creation and relationship linking for Appointment."""
        appt = Appointment.objects.create(
            appointment_datetime=timezone.now(),
            appointment_status="COMPLETED",
            disease=self.disease,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
            op_number="OP-101"
        )
        self.assertEqual(appt.disease.name, "Seasonal Flu")
        self.assertEqual(appt.patient.first_name, "Jane")
        self.assertEqual(appt.op_number, "OP-101")

    def test_appointment_query_by_date_range(self):
        """Test filtering appointments by date ranges (critical for analytics)."""
        now = timezone.now()
        Appointment.objects.create(
            appointment_datetime=now,
            appointment_status="C", disease=self.disease, clinic=self.clinic, 
            doctor=self.doctor, patient=self.patient, op_number="A1"
        )
        Appointment.objects.create(
            appointment_datetime=now - timedelta(days=10),
            appointment_status="C", disease=self.disease, clinic=self.clinic, 
            doctor=self.doctor, patient=self.patient, op_number="A2"
        )
        
        recent_count = Appointment.objects.filter(
            appointment_datetime__range=(now - timedelta(days=5), now + timedelta(hours=1))
        ).count()
        self.assertEqual(recent_count, 1)

    def test_on_delete_cascade_protection(self):
        """Test that appointments are removed when the linked disease is deleted."""
        Appointment.objects.create(
            appointment_datetime=timezone.now(),
            appointment_status="C", disease=self.disease, clinic=self.clinic, 
            doctor=self.doctor, patient=self.patient, op_number="A3"
        )
        self.disease.delete()
        self.assertEqual(Appointment.objects.count(), 0)
