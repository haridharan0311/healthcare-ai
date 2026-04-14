from django.test import TestCase
from django.utils import timezone
from core.models import Clinic, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine

class InventoryModelTestCase(TestCase):
    """Test inventory models and business logic."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Test Clinic", clinic_address_1="123 Main St")
        self.disease = Disease.objects.create(name="Flu", season="Winter", severity=2)
        self.doctor = Doctor.objects.create(first_name="Doc", last_name="Who", qualification="MD", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="Jane", last_name="Doe", mobile_number="1234567890", clinic=self.clinic)
        self.appointment = Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient
        )

    def test_drug_master_stock_level(self):
        """Test basic drug master creation and stock."""
        drug = DrugMaster.objects.create(
            drug_name="Paracetamol",
            drug_strength="500mg",
            dosage_type="Tablet",
            current_stock=100,
            clinic=self.clinic
        )
        self.assertEqual(drug.current_stock, 100)
        self.assertEqual(str(drug), "Paracetamol")

    def test_prescription_line_denormalized_date(self):
        """Test that mapping prescription_date from header works automatically."""
        prescription_date = timezone.now().date()
        prescription = Prescription.objects.create(
            prescription_date=prescription_date,
            appointment=self.appointment,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient
        )
        drug = DrugMaster.objects.create(drug_name="A", clinic=self.clinic)
        
        line = PrescriptionLine.objects.create(
            prescription=prescription,
            drug=drug,
            quantity=10,
            disease=self.disease,
            duration="5 days"
        )
        
        # Verify the custom save() logic inherited the date
        self.assertEqual(line.prescription_date, prescription_date)
