"""
EXPORT DATA COMMAND
===================
Exports all database records to CSV files in the data/ folder.

This command creates a complete backup of the database in CSV format,
suitable for backup, migration, or re-import into another environment.

USAGE:
    python manage.py export_data

OUTPUT FILES (in data/ folder):
    - Clinic.csv: All clinic information
    - Doctor.csv: All doctor records with clinic associations
    - Patient.csv: All patient records with doctor/clinic associations
    - Disease.csv: All disease definitions with seasons and severity
    - DrugMaster.csv: All medicine inventory with stock levels
    - Appointment.csv: All appointment records with foreign keys
    - Prescription.csv: All prescription records
    - PrescriptionLine.csv: All prescription line items

FEATURES:
    - Handles NULL/empty foreign keys gracefully
    - UTF-8 encoding for international characters
    - CSV format compatible with import_data command
    - Progress messages for each export stage
    - Error handling with informative messages

EXAMPLE:
    $ python manage.py export_data
    Exporting Clinics...
    Exporting Diseases...
    ...
    ✅ ALL DATA EXPORTED SUCCESSFULLY TO CSV FILES

INTEGRATION:
    Part of the backup/migration workflow with import_data command.
    Always run optimize_db after import for best performance.

See Also:
    - import_data: Opposite operation (import CSV to database)
    - optimize_db: Add indexes for query performance
"""

import csv
import os
from django.core.management.base import BaseCommand
from core.models import Clinic, Doctor, Patient
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.models import Disease, Appointment


class Command(BaseCommand):
    help = "Export all database data to CSV files in the data/ folder"

    def handle(self, *args, **kwargs):
        base_path = "data/"
        
        # Create data directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)

        try:
            # ================== CLINIC ==================
            self.stdout.write("Exporting Clinics...")
            with open(base_path + "Clinic.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "clinic_name", "clinic_address_1"])
                writer.writeheader()
                for clinic in Clinic.objects.all():
                    writer.writerow({
                        "id": clinic.id,
                        "clinic_name": clinic.clinic_name,
                        "clinic_address_1": clinic.clinic_address_1
                    })

            # ================== DISEASE ==================
            self.stdout.write("Exporting Diseases...")
            with open(base_path + "Disease.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "season", "category", "severity", "is_active", "created_at"])
                writer.writeheader()
                for disease in Disease.objects.all():
                    writer.writerow({
                        "id": disease.id,
                        "name": disease.name,
                        "season": disease.season,
                        "category": disease.category,
                        "severity": disease.severity,
                        "is_active": disease.is_active,
                        "created_at": disease.created_at
                    })

            # ================== DOCTOR ==================
            self.stdout.write("Exporting Doctors...")
            with open(base_path + "Doctor.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "first_name", "last_name", "gender", "qualification", "clinic_id"])
                writer.writeheader()
                for doctor in Doctor.objects.all():
                    writer.writerow({
                        "id": doctor.id,
                        "first_name": doctor.first_name,
                        "last_name": doctor.last_name,
                        "gender": doctor.gender,
                        "qualification": doctor.qualification,
                        "clinic_id": doctor.clinic_id
                    })

            # ================== PATIENT ==================
            self.stdout.write("Exporting Patients...")
            with open(base_path + "Patient.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "first_name", "last_name", "gender", "title", "dob", "mobile_number", "address_line_1", "clinic_id", "doctor_id"])
                writer.writeheader()
                for patient in Patient.objects.all():
                    writer.writerow({
                        "id": patient.id,
                        "first_name": patient.first_name,
                        "last_name": patient.last_name,
                        "gender": patient.gender,
                        "title": patient.title,
                        "dob": patient.dob,
                        "mobile_number": patient.mobile_number,
                        "address_line_1": patient.address_line_1,
                        "clinic_id": patient.clinic_id,
                        "doctor_id": patient.doctor_id if patient.doctor_id else ""
                    })

            # ================== DRUG MASTER ==================
            self.stdout.write("Exporting DrugMaster...")
            with open(base_path + "DrugMaster.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "drug_name", "generic_name", "drug_strength", "dosage_type", "clinic_id"])
                writer.writeheader()
                for drug in DrugMaster.objects.all():
                    writer.writerow({
                        "id": drug.id,
                        "drug_name": drug.drug_name,
                        "generic_name": drug.generic_name,
                        "drug_strength": drug.drug_strength,
                        "dosage_type": drug.dosage_type,
                        "clinic_id": drug.clinic_id
                    })

            # ================== APPOINTMENT ==================
            self.stdout.write("Exporting Appointments...")
            with open(base_path + "Appointment.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "appointment_datetime", "appointment_status", "op_number", "clinic_id", "doctor_id", "patient_id", "disease_id"])
                writer.writeheader()
                for appointment in Appointment.objects.all():
                    writer.writerow({
                        "id": appointment.id,
                        "appointment_datetime": appointment.appointment_datetime,
                        "appointment_status": appointment.appointment_status,
                        "op_number": appointment.op_number,
                        "clinic_id": appointment.clinic_id,
                        "doctor_id": appointment.doctor_id,
                        "patient_id": appointment.patient_id,
                        "disease_id": appointment.disease_id
                    })

            # ================== PRESCRIPTION ==================
            self.stdout.write("Exporting Prescriptions...")
            with open(base_path + "Prescription.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "prescription_date", "appointment_id", "clinic_id", "doctor_id", "patient_id"])
                writer.writeheader()
                for prescription in Prescription.objects.all():
                    writer.writerow({
                        "id": prescription.id,
                        "prescription_date": prescription.prescription_date,
                        "appointment_id": prescription.appointment_id,
                        "clinic_id": prescription.clinic_id,
                        "doctor_id": prescription.doctor_id,
                        "patient_id": prescription.patient_id
                    })

            # ================== PRESCRIPTION LINE ==================
            self.stdout.write("Exporting PrescriptionLines...")
            with open(base_path + "PrescriptionLine.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "duration", "instructions", "quantity", "drug_id", "prescription_id", "disease_id"])
                writer.writeheader()
                for line in PrescriptionLine.objects.all():
                    writer.writerow({
                        "id": line.id,
                        "duration": line.duration,
                        "instructions": line.instructions,
                        "quantity": line.quantity,
                        "drug_id": line.drug_id,
                        "prescription_id": line.prescription_id,
                        "disease_id": line.disease_id if line.disease_id else ""
                    })

            self.stdout.write(self.style.SUCCESS("✅ ALL DATA EXPORTED SUCCESSFULLY TO CSV FILES"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ ERROR DURING EXPORT: {str(e)}"))
