from django.test import TestCase
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic, Doctor, Patient
from analytics.models import Appointment, Disease
from django.utils import timezone

class InventoryModelsTestCase(TestCase):
    """
    Unit tests for Inventory and Prescription system models.
    """

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Pharmacy Main", clinic_address_1="Central")
        self.doctor = Doctor.objects.create(first_name="Doc", gender="M", qualification="MD", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="P", last_name="1", gender="M", dob="2000-01-01", clinic=self.clinic)
        self.disease = Disease.objects.create(name="Cold", season="ALL", severity=1, created_at=timezone.now())
        self.appointment = Appointment.objects.create(
            appointment_datetime=timezone.now(), appointment_status="C",
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number="X1"
        )

    def test_drug_master_stock_management(self):
        """Test baseline stock levels in DrugMaster."""
        drug = DrugMaster.objects.create(
            drug_name="Paracetamol",
            drug_strength="500mg",
            dosage_type="Tablet",
            current_stock=100,
            clinic=self.clinic
        )
        self.assertEqual(drug.current_stock, 100)
        self.assertEqual(str(drug), "Paracetamol")

    def test_prescription_and_lines(self):
        """Test prescription creation and denormalized date logic."""
        drug = DrugMaster.objects.create(drug_name="A", drug_strength="1", dosage_type="T", clinic=self.clinic)
        rx = Prescription.objects.create(
            prescription_date=timezone.now().date(),
            appointment=self.appointment,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient
        )
        line = PrescriptionLine.objects.create(
            prescription=rx,
            drug=drug,
            quantity=10,
            instructions="Once daily",
            disease=self.disease
        )
        
        # Test the custom save() logic for denormalization
        self.assertEqual(line.prescription_date, rx.prescription_date)
        self.assertEqual(line.quantity, 10)

    def test_low_stock_filtering_logic(self):
        """Verify queries for identifying low stock items."""
        DrugMaster.objects.create(drug_name="Low", current_stock=2, clinic=self.clinic)
        DrugMaster.objects.create(drug_name="High", current_stock=200, clinic=self.clinic)
        
        low_stock_items = DrugMaster.objects.filter(current_stock__lt=10)
        self.assertEqual(low_stock_items.count(), 1)
        self.assertEqual(low_stock_items[0].drug_name, "Low")

    def test_zero_stock_boundary(self):
        """Test exact zero-stock filtering."""
        DrugMaster.objects.create(drug_name="Zero", current_stock=0, clinic=self.clinic)
        zero_stock = DrugMaster.objects.filter(current_stock=0)
        self.assertEqual(zero_stock.count(), 1)
        self.assertEqual(zero_stock[0].drug_name, "Zero")

    def test_prescription_line_explicit_date(self):
        """Test that PrescriptionLine doesn't override an explicitly provided date."""
        drug = DrugMaster.objects.create(drug_name="B", drug_strength="1", dosage_type="T", clinic=self.clinic)
        rx = Prescription.objects.create(
            prescription_date=timezone.now().date(),
            appointment=self.appointment,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient
        )
        past_date = timezone.now().date() - timedelta(days=10)
        line = PrescriptionLine.objects.create(
            prescription=rx,
            drug=drug,
            quantity=5,
            instructions="X",
            disease=self.disease,
            prescription_date=past_date
        )
        self.assertEqual(line.prescription_date, past_date)
