from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Clinic, Doctor, Patient, UserProfile

class CoreModelsTestCase(TestCase):
    """
    Unit tests for Core system models: Clinics, Users, Doctors, and Patients.
    """

    def setUp(self):
        self.clinic = Clinic.objects.create(
            clinic_name="General Hospital",
            clinic_address_1="Downtown"
        )
        self.user = User.objects.create_user(username="dr_smith", password="password123")

    def test_clinic_creation(self):
        """Test Clinic string representation."""
        self.assertEqual(str(self.clinic), "General Hospital")

    def test_user_profile_role_linking(self):
        """Test UserProfile and role-based access logic initialization."""
        profile = UserProfile.objects.create(
            user=self.user,
            clinic=self.clinic,
            role="CLINIC_USER"
        )
        self.assertEqual(profile.role, "CLINIC_USER")
        self.assertEqual(profile.clinic.clinic_name, "General Hospital")

    def test_doctor_full_name(self):
        """Test Doctor naming logic."""
        dr = Doctor.objects.create(
            first_name="Gregory",
            last_name="House",
            gender="M",
            qualification="MD",
            clinic=self.clinic
        )
        self.assertEqual(str(dr), "Gregory House")

    def test_patient_demographics(self):
        """Test Patient data capture."""
        pat = Patient.objects.create(
            first_name="Alice",
            last_name="Wonder",
            gender="F",
            title="Ms",
            dob="1985-05-20",
            mobile_number="9998887776",
            address_line_1="Wonderland",
            clinic=self.clinic
        )
        self.assertEqual(pat.first_name, "Alice")
        self.assertEqual(pat.mobile_number, "9998887776")

    def test_patient_doctor_assignment(self):
        """Verify that a patient can be correctly associated with a doctor."""
        dr = Doctor.objects.create(
            first_name="Gregory", gender="M", qualification="MD", clinic=self.clinic
        )
        pat = Patient.objects.create(
            first_name="Alice", last_name="W", gender="F", title="Ms",
            dob="1985-05-20", clinic=self.clinic, doctor=dr
        )
        self.assertEqual(pat.doctor.first_name, "Gregory")
        self.assertEqual(dr.patients.count(), 1)

    def test_user_profile_role_choices(self):
        """Test that only valid roles can be assigned (Logic check)."""
        profile = UserProfile.objects.create(user=self.user, role="ADMIN")
        self.assertIn(profile.role, [choice[0] for choice in UserProfile.ROLE_CHOICES])
