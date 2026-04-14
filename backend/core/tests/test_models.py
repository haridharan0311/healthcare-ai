from django.test import TestCase
from core.models import Clinic, Doctor, Patient

class CoreModelTestCase(TestCase):
    """Test core foundation models."""

    def test_clinic_creation(self):
        clinic = Clinic.objects.create(clinic_name="Alpha Clinic", clinic_address_1="Address")
        self.assertEqual(str(clinic), "Alpha Clinic")

    def test_doctor_full_name(self):
        clinic = Clinic.objects.create(clinic_name="A", clinic_address_1="B")
        doctor = Doctor.objects.create(
            first_name="John", 
            last_name="Doe", 
            qualification="MBBS", 
            clinic=clinic
        )
        self.assertEqual(f"{doctor.first_name} {doctor.last_name}", "John Doe")
