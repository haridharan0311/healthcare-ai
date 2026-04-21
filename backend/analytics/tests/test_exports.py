import csv
import io
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from django.utils import timezone
from datetime import date, timedelta

class AnalyticsExportAPITestCase(APITestCase):
    """
    Focused test suite for CSV Export endpoints.
    Ensures that data is correctly formatted, headers are preserved, 
    and multi-part reporting logic remains consistent.
    """

    def setUp(self):
        # Setup Auth
        self.user_admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        UserProfile.objects.create(user=self.user_admin, role="ADMIN")
        
        # Setup Core Data
        self.clinic = Clinic.objects.create(clinic_name="Alpha", clinic_address_1="City")
        self.disease = Disease.objects.create(name="Flu", season="WINTER", severity=2, created_at=timezone.now())
        self.drug = DrugMaster.objects.create(drug_name="Aspirin", current_stock=10, clinic=self.clinic)
        
        # Seed Appointment for Trends
        self.doctor = Doctor.objects.create(first_name="Dr", clinic=self.clinic, gender="M", qualification="MD")
        self.patient = Patient.objects.create(first_name="P", last_name="L", clinic=self.clinic, gender="M", dob="1990-01-01")
        
        self.appointment = Appointment.objects.create(
            appointment_datetime=timezone.now(), appointment_status="C",
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient, op_number="X1"
        )

        # Seed Usage for Restock/Depletion
        self.prescription = Prescription.objects.create(
            prescription_date=date.today(),
            appointment=self.appointment,
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient
        )
        PrescriptionLine.objects.create(
            prescription=self.prescription,
            drug=self.drug,
            quantity=50,
            disease=self.disease
        )

    def _get_csv_content(self, response):
        """Helper to parse CSV response into list of rows, skipping empty ones."""
        content = response.content.decode('utf-8')
        stream = io.StringIO(content)
        reader = csv.reader(stream)
        return [row for row in reader if row]

    # ── Disease Trends Export ──────────────────────────────────────

    def test_export_disease_trends(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('export-trends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        rows = self._get_csv_content(response)
        # Header + at least one data row (for Flu)
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0][0], 'Disease')
        self.assertIn('Flu', [r[0] for r in rows])

    # ── Spike Alerts Export ────────────────────────────────────────

    def test_export_spike_alerts(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('export-spikes')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self._get_csv_content(response)
        self.assertEqual(rows[0][0], 'Disease')
        # Check an index that exists in the header (e.g. index 7 for 'Is Spike')
        self.assertIn('Is Spike', rows[0])

    # ── Restock Suggestions Export ─────────────────────────────────

    def test_export_restock_suggestions(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('export-restock')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self._get_csv_content(response)
        self.assertIn('Drug Name', rows[0])
        self.assertIn('Aspirin', [r[0] for r in rows])

    # ── Low Stock Alerts ───────────────────────────────────────────

    def test_export_low_stock_alerts(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('export-low-stock-alerts')
        response = self.client.get(url, {'threshold': 50})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self._get_csv_content(response)
        # Aspirin has 10 units, which is <= threshold 50
        self.assertIn('Aspirin', [r[0] for r in rows])

    # ── Stock Depletion (ML Driven) ────────────────────────────────

    def test_export_stock_depletion(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('export-stock-depletion')
        # Detailed view for specific drug
        response = self.client.get(url, {'drug_name': 'Aspirin'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self._get_csv_content(response)
        self.assertIn('Metric', rows[1]) # Header row
        self.assertIn('Days Until Depletion', [r[0] for r in rows])

    # ── Consolidated Intelligence Report ───────────────────────────

    def test_export_consolidated_report(self):
        self.client.force_authenticate(user=self.user_admin)
        url = reverse('export-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self._get_csv_content(response)
        # Check for section headers
        self.assertIn('DECISION SUPPORT SUMMARY', [r[0] for r in rows])
        self.assertIn('STRATEGIC RECOMMENDATIONS', [r[0] for r in rows])
