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
        base_path = "data/"
        
        # Check if data directory exists
        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR(f"❌ ERROR: {base_path} directory not found"))
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

                # ---------------- DISEASE ----------------
                self.stdout.write("Importing Diseases...")
                diseases = []
                with open(base_path + "Disease.csv") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dt = parse_datetime(row["created_at"])
                        if dt:
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
                        if dt:
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

                        lines.append(PrescriptionLine(
                            id=int(row["id"]),
                            duration=row["duration"],
                            instructions=row["instructions"],
                            prescription=prescription_map[int(row["prescription_id"])],
                            disease=disease_obj,
                            quantity=int(row["quantity"]),
                            drug=drug_map[int(row["drug_id"])]
                        ))
                PrescriptionLine.objects.bulk_create(lines, batch_size=1000)

                self.stdout.write(self.style.SUCCESS("✅ ALL DATA IMPORTED SUCCESSFULLY"))

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"❌ ERROR: CSV file not found - {str(e)}"))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(f"❌ ERROR: Missing column in CSV - {str(e)}"))
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"❌ ERROR: Invalid data format - {str(e)}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ ERROR: {str(e)}"))
