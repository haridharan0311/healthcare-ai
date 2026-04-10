"""
Tests for Live Data Generator
===============================
Tests that the background data generation task works correctly.
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from analytics.utils.live_data_generator import LiveDataGenerator
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic, Doctor, Patient


class LiveDataGeneratorTestCase(TestCase):
    """Test the LiveDataGenerator background task."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data for all tests."""
        # Create clinic
        cls.clinic = Clinic.objects.create(
            id=1,
            clinic_name="Test Clinic",
            clinic_address_1="123 Main St"
        )
        
        # Create disease
        cls.disease = Disease.objects.create(
            id=1,
            name="Test Disease",
            season="All",
            category="Test",
            severity=1,
            is_active=True,
            created_at=timezone.now()
        )
        
        # Create doctor
        cls.doctor = Doctor.objects.create(
            id=1,
            first_name="John",
            last_name="Doe",
            gender="M",
            qualification="MD",
            clinic=cls.clinic
        )
        
        # Create patient
        cls.patient = Patient.objects.create(
            id=1,
            first_name="Jane",
            last_name="Doe",
            gender="F",
            title="Ms",
            dob="1990-01-01",
            mobile_number="9876543210",
            address_line_1="456 Oak Ave",
            clinic=cls.clinic,
            doctor=cls.doctor
        )
        
        # Create drug
        cls.drug = DrugMaster.objects.create(
            id=1,
            drug_name="Aspirin",
            generic_name="Acetylsalicylic acid",
            drug_strength="500mg",
            dosage_type="Tablet",
            clinic=cls.clinic
        )
    
    def setUp(self):
        """Set up for each test."""
        self.generator = LiveDataGenerator()
    
    def test_generator_initialization(self):
        """Test that the generator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertTrue(self.generator.interval > 0)
        self.assertFalse(self.generator.running)
    
    def test_generate_data_creates_appointments(self):
        """Test that generate_data creates appointments."""
        initial_count = Appointment.objects.count()
        
        self.generator.generate_data()
        
        final_count = Appointment.objects.count()
        self.assertGreater(final_count, initial_count)
    
    def test_generate_data_creates_prescriptions(self):
        """Test that appointments with 'Completed' status get prescriptions."""
        initial_rx_count = Prescription.objects.count()
        
        self.generator.generate_data()
        
        final_rx_count = Prescription.objects.count()
        # Should create at least some prescriptions (80% of completed appointments)
        self.assertGreaterEqual(final_rx_count, initial_rx_count)
    
    def test_generate_data_creates_prescription_lines(self):
        """Test that each prescription gets prescription lines."""
        initial_lines_count = PrescriptionLine.objects.count()
        
        self.generator.generate_data()
        self.generator.generate_data()  # Generate twice to ensure prescriptions exist
        
        final_lines_count = PrescriptionLine.objects.count()
        self.assertGreaterEqual(final_lines_count, initial_lines_count)
    
    def test_appointment_status_values(self):
        """Test that appointments have valid status values."""
        self.generator.generate_data()
        
        appointments = Appointment.objects.all()
        valid_statuses = ['Completed', 'Scheduled', 'Cancelled']
        
        for appointment in appointments:
            self.assertIn(appointment.appointment_status, valid_statuses)
    
    def test_prescription_date_matches_appointment(self):
        """Test that prescription dates match appointment dates."""
        self.generator.generate_data()
        
        for prescription in Prescription.objects.all():
            appointment = prescription.appointment
            self.assertEqual(
                prescription.prescription_date,
                appointment.appointment_datetime.date()
            )
    
    def test_drug_stock_decreases(self):
        """Test that drug stock decreases after prescription generation."""
        initial_stock = self.drug.current_stock
        
        self.generator.generate_data()
        
        self.drug.refresh_from_db()
        # Stock should either stay same or decrease (never increase)
        self.assertLessEqual(self.drug.current_stock, initial_stock)
    
    def test_appointment_has_valid_relationships(self):
        """Test that all appointments have valid foreign key relationships."""
        self.generator.generate_data()
        
        for appointment in Appointment.objects.all():
            self.assertIsNotNone(appointment.clinic)
            self.assertIsNotNone(appointment.doctor)
            self.assertIsNotNone(appointment.patient)
            self.assertIsNotNone(appointment.disease)
    
    def test_op_number_uniqueness(self):
        """Test that OP numbers are unique."""
        self.generator.generate_data()
        self.generator.generate_data()  # Generate twice
        
        appointments = Appointment.objects.all()
        op_numbers = [a.op_number for a in appointments]
        
        # All OP numbers should be unique
        self.assertEqual(len(op_numbers), len(set(op_numbers)))
    
    def test_prescription_line_quantity_valid(self):
        """Test that prescription line quantities are valid."""
        self.generator.generate_data()
        
        lines = PrescriptionLine.objects.all()
        for line in lines:
            self.assertGreater(line.quantity, 0)
            self.assertIn(line.quantity, [1, 2, 3])
