from django.test import TestCase
from django.utils import timezone
from datetime import date
from analytics.models import Disease, Appointment
from core.models import Clinic, Doctor, Patient
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.services.usage import UsageIntelligence

class UsageIntelligenceTestCase(TestCase):
    """Feature 3: Medicine Usage Intelligence tests."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Usage Clinic")
        self.disease = Disease.objects.create(name="Dengue")
        self.doc = Doctor.objects.create(first_name="DrU", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatU", dob="2000-01-01", clinic=self.clinic)
        self.drug = DrugMaster.objects.create(drug_name="D-Med", current_stock=100, clinic=self.clinic)

    def test_usage_pattern_mapping(self):
        intel = UsageIntelligence()
        appt = Appointment.objects.create(appointment_datetime=timezone.now(), disease=self.disease, clinic=self.clinic, doctor=self.doc, patient=self.pat, op_number="U-1")
        rx = Prescription.objects.create(prescription_date=date.today(), appointment=appt, clinic=self.clinic, doctor=self.doc, patient=self.pat)
        PrescriptionLine.objects.create(prescription=rx, drug=self.drug, quantity=5, disease=self.disease)
        
        res = intel.get_medicine_usage_per_disease(disease_name="Dengue")
        patterns = res.get('top_medicines', [])
        self.assertEqual(patterns[0]['drug_name'], "D-Med")
        self.assertEqual(patterns[0]['total_quantity'], 5)

