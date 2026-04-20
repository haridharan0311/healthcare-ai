from django.test import TestCase
from django.utils import timezone
from core.models import Clinic, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster
from analytics.utils.live_data_generator import LiveDataGenerator

class LiveDataGeneratorTest(TestCase):
    def setUp(self):
        # Create minimal reference data
        self.clinic = Clinic.objects.create(clinic_name="Test Clinic", clinic_address_1="123 Test St")
        self.disease = Disease.objects.create(
            name="Fever", 
            season="All", 
            is_active=True,
            created_at=timezone.now()
        )
        self.drug = DrugMaster.objects.create(
            drug_name="Paracetamol", 
            generic_name="Para", 
            drug_strength="500mg",
            dosage_type="Tablet",
            current_stock=1000,
            clinic=self.clinic
        )
        # Note: We won't create doctor/patient here to test the "Auto-Onboarding" logic
        
        self.generator = LiveDataGenerator()

    def test_generator_auto_onboarding(self):
        """Test that the generator creates missing doctors/patients for a clinic."""
        self.generator.target_clinic_id = self.clinic.id
        
        # Verify initial state
        self.assertEqual(Doctor.objects.filter(clinic=self.clinic).count(), 0)
        self.assertEqual(Patient.objects.filter(clinic=self.clinic).count(), 0)
        
        # Run one generation cycle
        self.generator.generate_data()
        
        # Verify auto-onboarding worked
        self.assertEqual(Doctor.objects.filter(clinic=self.clinic).count(), 1)
        self.assertEqual(Patient.objects.filter(clinic=self.clinic).count(), 1)
        
        # Verify data was generated
        self.assertGreater(Appointment.objects.filter(clinic=self.clinic).count(), 0)

    def test_generator_clinic_filtering(self):
        """Test that the generator respects the target_clinic_id filter."""
        other_clinic = Clinic.objects.create(clinic_name="Other Clinic")
        self.generator.target_clinic_id = self.clinic.id
        
        # Run generation
        self.generator.generate_data()
        
        # All appointments should belong to the target clinic
        appts = Appointment.objects.all()
        for appt in appts:
            self.assertEqual(appt.clinic, self.clinic)
            self.assertNotEqual(appt.clinic, other_clinic)

    def test_generator_status_updates(self):
        """Test that start() updates settings even if already running."""
        self.generator.start(interval=60)
        self.assertTrue(self.generator.running)
        self.assertEqual(self.generator.interval, 60)
        
        # Update without stopping
        self.generator.start(interval=10, target_clinic_id=99)
        self.assertEqual(self.generator.interval, 10)
        self.assertEqual(self.generator.target_clinic_id, 99)
        
        self.generator.stop()
