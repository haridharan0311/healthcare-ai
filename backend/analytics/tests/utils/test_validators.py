from datetime import date, timedelta
from django.test import TestCase
from analytics.utils.validators import (
    validate_date_range, validate_positive_int, 
    validate_disease_name, ValidationError, APIParameterValidator
)
from analytics.models import Appointment, Disease
from core.models import Clinic, Doctor, Patient
from django.utils import timezone

class ValidatorsTestCase(TestCase):
    """Tests for analytics utility validators."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Validator Clinic")
        self.disease = Disease.objects.create(name="Flu")
        self.doc = Doctor.objects.create(first_name="DrV", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatV", dob="2000-01-01", clinic=self.clinic)

    def test_date_range_validation(self):
        # 1. Valid range
        start, end = validate_date_range("2024-01-01", "2024-01-31")
        self.assertEqual(start, date(2024, 1, 1))
        self.assertEqual(end, date(2024, 1, 31))

        # 2. Invalid format
        with self.assertRaises(ValidationError):
            validate_date_range("invalid", "2024-01-01")

        # 3. Start > End
        with self.assertRaises(ValidationError):
            validate_date_range("2024-01-31", "2024-01-01")

        # 4. Exceeds max days
        with self.assertRaises(ValidationError):
            validate_date_range("2020-01-01", "2024-01-01", max_days=365)

    def test_positive_int_validation(self):
        # 1. Valid int
        self.assertEqual(validate_positive_int("10"), 10)
        
        # 2. Below min
        with self.assertRaises(ValidationError):
            validate_positive_int(0, min_value=1)
            
        # 3. Above max
        with self.assertRaises(ValidationError):
            validate_positive_int(100, max_value=50)
            
        # 4. Default fallback
        self.assertEqual(validate_positive_int("abc", default=30), 30)

    def test_disease_name_validation(self):
        self.assertEqual(validate_disease_name("  Fever  "), "Fever")
        with self.assertRaises(ValidationError):
            validate_disease_name("")
        with self.assertRaises(ValidationError):
            validate_disease_name(None)

    def test_api_parameter_validator_chaining(self):
        params = {'days': '60', 'disease': 'Dengue'}
        validator = APIParameterValidator(params)
        res = (validator
            .add_int('days', min_value=1, max_value=100)
            .add_string('disease', required=True)
            .validate())
        
        self.assertEqual(res['days'], 60)
        self.assertEqual(res['disease'], "Dengue")
