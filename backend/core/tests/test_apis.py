from django.test import TestCase
from rest_framework.test import APIClient
from core.models import Clinic, Doctor

class CoreAPITestCase(TestCase):
    """Test core APIs."""

    def setUp(self):
        self.client = APIClient()
        self.clinic = Clinic.objects.create(clinic_name="Alpha", clinic_address_1="A")
        self.doctor = Doctor.objects.create(first_name="Jane", last_name="Doe", qualification="MD", clinic=self.clinic)

    def test_dropdown_options_endpoint(self):
        """Verify dropdown options return foundational data."""
        response = self.client.get('/api/crud/dropdowns/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('doctors', data)
        self.assertIn('clinics', data)
        self.assertTrue(any(d['id'] == self.doctor.id for d in data['doctors']))
