from django.test import TestCase
from analytics.utils.query_optimization import (
    get_appointments_optimized, get_prescription_lines_optimized,
    get_drugs_optimized, get_diseases_optimized
)
from analytics.models import Appointment, Disease
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic, Doctor, Patient
from django.utils import timezone
from datetime import date

class QueryOptimizationTestCase(TestCase):
    """Tests for optimized query builders."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Opt Clinic")
        self.disease = Disease.objects.create(name="Opt Disease")
        self.doc = Doctor.objects.create(first_name="DrOpt", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatOpt", dob="2000-01-01", clinic=self.clinic)
        self.drug = DrugMaster.objects.create(drug_name="Opt Drug", current_stock=10, clinic=self.clinic)
        
        self.appt = Appointment.objects.create(
            appointment_datetime=timezone.now(),
            disease=self.disease, clinic=self.clinic, doctor=self.doc, patient=self.pat,
            op_number="OPT-1"
        )
        self.rx = Prescription.objects.create(
            prescription_date=date.today(), appointment=self.appt,
            clinic=self.clinic, doctor=self.doc, patient=self.pat
        )
        self.line = PrescriptionLine.objects.create(
            prescription=self.rx, drug=self.drug, quantity=1, disease=self.disease
        )

    def test_appointments_optimized_returns_data(self):
        qs = get_appointments_optimized().filter(id=self.appt.id)
        appt = qs.first()
        self.assertEqual(appt.disease.name, "Opt Disease")
        self.assertEqual(appt.clinic.clinic_name, "Opt Clinic")

    def test_prescription_lines_optimized_returns_data(self):
        qs = get_prescription_lines_optimized().filter(id=self.line.id)
        line = qs.first()
        self.assertEqual(line.drug.drug_name, "Opt Drug")
        self.assertEqual(line.disease.name, "Opt Disease")
        self.assertEqual(line.prescription.clinic.clinic_name, "Opt Clinic")

    def test_drugs_optimized_filtering(self):
        qs = get_drugs_optimized(clinic_id=self.clinic.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().drug_name, "Opt Drug")

    def test_diseases_optimized_active_only(self):
        self.disease.is_active = False
        self.disease.save()
        qs = get_diseases_optimized()
        self.assertEqual(qs.count(), 0)
