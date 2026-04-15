"""
IMPORT DATA COMMAND
===================
Imports all database records from CSV files in the data/ folder.

This command restores a database from exported CSV files. It handles foreign key
relationships, validates data, and provides comprehensive error reporting.

USAGE:
    python manage.py import_data

REQUIRED FILES (in data/ folder):
    - Clinic.csv (required first)
    - Disease.csv
    - Doctor.csv (requires Clinic data)
    - Patient.csv (requires Clinic and Doctor data)
    - DrugMaster.csv (requires Clinic data)
    - Appointment.csv (requires Disease/Clinic/Doctor/Patient)
    - Prescription.csv (requires Appointment/Clinic/Doctor/Patient)
    - PrescriptionLine.csv (requires Prescription/Drug/Disease)

IMPORT ORDER:
    The command automatically imports in correct order to resolve foreign keys:
    1. Clinic (base)
    2. Disease (base)
    3. Doctor (references Clinic)
    4. Patient (references Clinic, Doctor)
    5. DrugMaster (references Clinic)
    6. Appointment (references all above)
    7. Prescription (references Appointment)
    8. PrescriptionLine (references Prescription)

FEATURES:
    - Validates directory and file existence
    - Handles missing/optional fields (nullable FK)
    - Transaction support (all-or-nothing atomic operation)
    - Comprehensive error messages
    - Batch processing for performance (batch_size=1000)
    - DateTime parsing with timezone awareness

ERROR HANDLING:
    - FileNotFoundError: CSV file doesn't exist
    - KeyError: Missing required column in CSV
    - ValueError: Invalid data format
    - Generic exceptions: Other database/FK errors

EXAMPLE:
    $ python manage.py import_data
    Importing Clinics...
    Importing Diseases...
    ...
     ALL DATA IMPORTED SUCCESSFULLY

TROUBLESHOOTING:
    Q: "Duplicate entry for key" error
    A: Data already exists. Delete existing data first:
       python manage.py flush  (caution: deletes all data)
    
    Q: "Missing column" error
    A: Check data/* CSV files have correct headers

INTEGRATION:
    Part of the backup/migration workflow with export_data command.
    After import, run: python manage.py optimize_db

See Also:
    - export_data: Opposite operation (export database to CSV)
    - optimize_db: Add database indexes for performance
"""

import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction

from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

from core.models import Clinic, Doctor, Patient
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.models import Disease, Appointment


class Command(BaseCommand):
    help = "Optimized CSV Import"

    def handle(self, *args, **kwargs):
        base_path = "../data/"
        
        # Check if data directory exists
        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR(f" ERROR: {base_path} directory not found"))
            return

        try:
            with transaction.atomic():

                # ---------------- CLINIC ----------------
                self.stdout.write("Importing Clinics...")
                clinics = []
                with open(base_path + "Clinic.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        clinics.append(Clinic(
                            id=int(row["id"]),
                            clinic_name=row["clinic_name"],
                            clinic_address_1=row["clinic_address_1"]
                        ))
                Clinic.objects.bulk_create(clinics, batch_size=1000)

                clinic_map = {c.id: c for c in Clinic.objects.all()}

                # ---------------- USERS ----------------
                self.stdout.write("Importing Users & Profiles...")
                from django.contrib.auth.models import User
                from core.models import UserProfile
                
                with open(base_path + "users.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Create or get user
                        user, created = User.objects.get_or_create(
                            username=row["username"],
                            defaults={
                                "email": row["email"],
                                "date_joined": make_aware(parse_datetime(row["date_joined"])) if row["date_joined"] else date.today(),
                                "last_login": make_aware(parse_datetime(row["last_login"])) if row["last_login"] else None,
                            }
                        )
                        # Set hashed password directly
                        user.password = row["password"]
                        user.save()
                        
                        # Create/Update profile
                        clinic_id = row.get("clinic_id")
                        clinic_obj = clinic_map.get(int(clinic_id)) if clinic_id and clinic_id.strip() else None
                        
                        UserProfile.objects.update_or_create(
                            user=user,
                            defaults={
                                "clinic": clinic_obj,
                                "role": row["role"]
                            }
                        )

                # ---------------- DISEASE ----------------
                self.stdout.write("Importing Diseases...")
                diseases = []
                with open(base_path + "Disease.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dt = parse_datetime(row["created_at"])
                        if dt and dt.tzinfo is None:
                            dt = make_aware(dt)

                        diseases.append(Disease(
                            id=int(row["id"]),
                            name=row["name"],
                            season=row["season"],
                            category=row["category"],
                            severity=int(row["severity"]),
                            is_active=row["is_active"] == "True",
                            created_at=dt
                        ))
                Disease.objects.bulk_create(diseases, batch_size=1000)

                disease_map = {d.id: d for d in Disease.objects.all()}

                # ---------------- DOCTOR ----------------
                self.stdout.write("Importing Doctors...")
                doctors = []
                with open(base_path + "Doctor.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        doctors.append(Doctor(
                            id=int(row["id"]),
                            first_name=row["first_name"],
                            last_name=row["last_name"],
                            gender=row["gender"],
                            qualification=row["qualification"],
                            clinic=clinic_map[int(row["clinic_id"])]
                        ))
                Doctor.objects.bulk_create(doctors, batch_size=1000)

                doctor_map = {d.id: d for d in Doctor.objects.all()}

                # ---------------- PATIENT ----------------
                self.stdout.write("Importing Patients...")
                patients = []
                with open(base_path + "Patient.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        doctor_id_val = row.get("doctor_id", "").strip()
                        doctor_obj = doctor_map.get(int(doctor_id_val)) if doctor_id_val else None

                        patients.append(Patient(
                            id=int(row["id"]),
                            first_name=row["first_name"],
                            last_name=row["last_name"],
                            gender=row["gender"],
                            title=row["title"],
                            dob=row["dob"],
                            mobile_number=row["mobile_number"],
                            address_line_1=row["address_line_1"],
                            clinic=clinic_map[int(row["clinic_id"])],
                            doctor=doctor_obj
                        ))
                Patient.objects.bulk_create(patients, batch_size=1000)

                patient_map = {p.id: p for p in Patient.objects.all()}

                # ---------------- DRUG MASTER ----------------
                self.stdout.write("Importing DrugMaster...")
                drugs = []
                with open(base_path + "DrugMaster.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        drugs.append(DrugMaster(
                            id=int(row["id"]),
                            drug_name=row["drug_name"],
                            generic_name=row["generic_name"],
                            drug_strength=row["drug_strength"],
                            dosage_type=row["dosage_type"],
                            current_stock=int(row["current_stock"]),
                            clinic=clinic_map[int(row["clinic_id"])]
                        ))
                DrugMaster.objects.bulk_create(drugs, batch_size=1000)

                drug_map = {d.id: d for d in DrugMaster.objects.all()}

                # ---------------- APPOINTMENT ----------------
                self.stdout.write("Importing Appointments...")
                appointments = []
                with open(base_path + "Appointment.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dt = parse_datetime(row["appointment_datetime"])
                        if dt and dt.tzinfo is None:
                            dt = make_aware(dt)

                        appointments.append(Appointment(
                            id=int(row["id"]),
                            appointment_datetime=dt,
                            appointment_status=row["appointment_status"],
                            disease=disease_map[int(row["disease_id"])],
                            clinic=clinic_map[int(row["clinic_id"])],
                            doctor=doctor_map[int(row["doctor_id"])],
                            patient=patient_map[int(row["patient_id"])],
                            op_number=row["op_number"]
                        ))
                Appointment.objects.bulk_create(appointments, batch_size=1000)

                appointment_map = {a.id: a for a in Appointment.objects.all()}

                # ---------------- PRESCRIPTION ----------------
                self.stdout.write("Importing Prescriptions...")
                prescriptions = []
                with open(base_path + "Prescription.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        prescriptions.append(Prescription(
                            id=int(row["id"]),
                            prescription_date=row["prescription_date"],
                            appointment=appointment_map[int(row["appointment_id"])],
                            clinic=clinic_map[int(row["clinic_id"])],
                            doctor=doctor_map[int(row["doctor_id"])],
                            patient=patient_map[int(row["patient_id"])]
                        ))
                Prescription.objects.bulk_create(prescriptions, batch_size=1000)

                prescription_map = {p.id: p for p in Prescription.objects.all()}

                # ---------------- PRESCRIPTION LINE ----------------
                self.stdout.write("Importing PrescriptionLines...")
                lines = []
                with open(base_path + "PrescriptionLine.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        disease_id_val = row.get("disease_id", "").strip()
                        disease_obj = disease_map.get(int(disease_id_val)) if disease_id_val else None

                        prescription_obj = prescription_map[int(row["prescription_id"])]
                        lines.append(PrescriptionLine(
                            id=int(row["id"]),
                            duration=row["duration"],
                            instructions=row["instructions"],
                            prescription=prescription_obj,
                            prescription_date=prescription_obj.prescription_date,
                            disease=disease_obj,
                            quantity=int(row["quantity"]),
                            drug=drug_map[int(row["drug_id"])]
                        ))
                PrescriptionLine.objects.bulk_create(lines, batch_size=1000)

                self.stdout.write(self.style.SUCCESS(" ALL DATA IMPORTED SUCCESSFULLY"))

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f" ERROR: CSV file not found - {str(e)}"))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(f" ERROR: Missing column in CSV - {str(e)}"))
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f" ERROR: Invalid data format - {str(e)}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f" ERROR: {str(e)}"))

