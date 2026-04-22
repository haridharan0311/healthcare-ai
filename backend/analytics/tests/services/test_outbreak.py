from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from analytics.models import Disease, Appointment
from core.models import Clinic, Doctor, Patient
from analytics.services.spike_detection import SpikeDetectionService

class OutbreakServiceTestCase(TestCase):
    """Feature 2: Early Outbreak Detection tests."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Outbreak Clinic")
        self.disease = Disease.objects.create(name="Flu")
        self.doc = Doctor.objects.create(first_name="DrO", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatO", dob="2000-01-01", clinic=self.clinic)

    def test_monotonic_outbreak_detection(self):
        """Feature 2: Verify consistent upward trend detection."""
        # Seed 4 days: 5, 10, 15, 20 (strictly increasing)
        base = timezone.now() - timedelta(days=4)
        for d in range(4):
            count = (d + 1) * 5
            for i in range(count):
                Appointment.objects.create(
                    appointment_datetime=base + timedelta(days=d),
                    disease=self.disease, clinic=self.clinic, doctor=self.doc, patient=self.pat,
                    op_number=f"O-{d}-{i}"
                )
        
        service = SpikeDetectionService()
        outbreaks = service.detect_early_outbreaks(min_days=3, min_cases=5)
        
        # Should find Flu in the list
        flu_alert = next((o for o in outbreaks if o['disease_name'] == 'Flu'), None)
        self.assertIsNotNone(flu_alert)
        self.assertEqual(flu_alert['severity'], 'critical') # score > 100
