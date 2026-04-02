"""
Tests for Data Management Commands
===================================
Tests for export_data, import_data, and optimize_db commands.
"""

import os
import csv
import tempfile
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from core.models import Clinic, Doctor, Patient
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.models import Disease, Appointment


class ExportDataCommandTestCase(TestCase):
    """Test the export_data management command."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.clinic = Clinic.objects.create(
            clinic_name="Test Clinic",
            clinic_address_1="123 Main St"
        )
        
        cls.disease = Disease.objects.create(
            name="Test Disease",
            season="All",
            category="Test",
            severity=1,
            is_active=True,
            created_at=timezone.now()
        )
        
        cls.doctor = Doctor.objects.create(
            first_name="John",
            last_name="Doe",
            gender="M",
            qualification="MD",
            clinic=cls.clinic
        )
        
        cls.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Doe",
            gender="F",
            title="Ms",
            dob="1990-01-01",
            mobile_number="9876543210",
            address_line_1="456 Oak Ave",
            clinic=cls.clinic
        )
    
    def test_export_data_command_runs(self):
        """Test that export_data command executes without errors."""
        out = StringIO()
        call_command('export_data', stdout=out)
        
        self.assertIn("EXPORTED SUCCESSFULLY", out.getvalue())
    
    def test_export_creates_csv_files(self):
        """Test that CSV files are created in data/ directory."""
        call_command('export_data')
        
        csv_files = ['Clinic.csv', 'Disease.csv', 'Doctor.csv']
        for csv_file in csv_files:
            path = os.path.join('data', csv_file)
            self.assertTrue(os.path.exists(path), f"{csv_file} was not created")
    
    def test_exported_csv_has_correct_headers(self):
        """Test that exported CSV files have correct column headers."""
        call_command('export_data')
        
        with open('data/Clinic.csv', 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            self.assertIn('id', headers)
            self.assertIn('clinic_name', headers)


class ImportDataCommandTestCase(TestCase):
    """Test the import_data management command."""
    
    def setUp(self):
        """Set up test data and CSV files."""
        # Create temporary CSV files for testing
        self.test_data = {
            'Clinic.csv': 'id,clinic_name,clinic_address_1\n1,Test,123 Main\n',
            'Disease.csv': 'id,name,season,category,severity,is_active,created_at\n1,Test,All,Test,1,True,\n',
        }
    
    def test_import_data_requires_csv_files(self):
        """Test that import_data handles missing CSV files gracefully."""
        # This should not raise an exception, just return early
        try:
            call_command('import_data')
        except Exception as e:
            # Only fail if it's not a file-related error
            self.fail(f"import_data should handle missing files: {e}")


class OptimizeDbCommandTestCase(TestCase):
    """Test the optimize_db management command."""
    
    def test_optimize_db_command_runs(self):
        """Test that optimize_db command executes without errors."""
        out = StringIO()
        call_command('optimize_db', stdout=out)
        
        output = out.getvalue()
        self.assertTrue(len(output) > 0, "optimize_db should produce output")
