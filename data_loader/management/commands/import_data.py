import csv
from django.core.management.base import BaseCommand

from core.models import Clinic, Doctor, Patient
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from analytics.models import Disease, Appointment


class Command(BaseCommand):
    help = "Import CSV data into database"

    def handle(self, *args, **kwargs):

        base_path = "data/"

        # ---------------- Clinic ----------------
        with open(base_path + "Clinic_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                Clinic.objects.create(
                    id=row["id"],
                    clinic_name=row["clinic_name"],
                    clinic_address_1=row["clinic_address_1"]
                )

        # ---------------- Disease ----------------
        with open(base_path + "Disease_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                Disease.objects.create(
                    id=row["id"],
                    name=row["name"],
                    season=row["season"],
                    category=row["category"],
                    severity=row["severity"],
                    is_active=row["is_active"] == "True",
                    created_at=row["created_at"]
                )

        # ---------------- Doctor ----------------
        with open(base_path + "Doctor_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                Doctor.objects.create(
                    id=row["id"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    gender=row["gender"],
                    qualification=row["qualification"],
                    clinic=Clinic.objects.get(id=row["clinic"])
                )

        # ---------------- Patient ----------------
        with open(base_path + "Patient_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                Patient.objects.create(
                    id=row["id"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    gender=row["gender"],
                    title=row["title"],
                    dob=row["dob"],
                    mobile_number=row["mobile_number"],
                    address_line_1=row["address_line_1"],
                    clinic=Clinic.objects.get(id=row["clinic"]),
                    doctor=Doctor.objects.filter(id=row["doctor"]).first()
                )

        # ---------------- DrugMaster ----------------
        with open(base_path + "DrugMaster_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                DrugMaster.objects.create(
                    id=row["id"],
                    drug_name=row["drug_name"],
                    generic_name=row["generic_name"],
                    drug_strength=row["drug_strength"],
                    dosage_type=row["dosage_type"],
                    clinic=Clinic.objects.get(id=row["clinic"])
                )

        # ---------------- Appointment ----------------
        with open(base_path + "Appointment_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                Appointment.objects.create(
                    id=row["id"],
                    appointment_datetime=row["appointment_datetime"],
                    appointment_status=row["appointment_status"],
                    disease=Disease.objects.get(id=row["disease"]),
                    clinic=Clinic.objects.get(id=row["clinic"]),
                    doctor=Doctor.objects.get(id=row["doctor"]),
                    patient=Patient.objects.get(id=row["patient"]),
                    op_number=row["op_number"]
                )

        # ---------------- Prescription ----------------
        with open(base_path + "Prescription_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                Prescription.objects.create(
                    id=row["id"],
                    prescription_date=row["prescription_date"],
                    appointment=Appointment.objects.get(id=row["appointment"]),
                    clinic=Clinic.objects.get(id=row["clinic"]),
                    doctor=Doctor.objects.get(id=row["doctor"]),
                    patient=Patient.objects.get(id=row["patient"])
                )

        # ---------------- PrescriptionLine ----------------
        with open(base_path + "PrescriptionLine_real.csv") as file:
            reader = csv.DictReader(file)
            for row in reader:
                PrescriptionLine.objects.create(
                    id=row["id"],
                    duration=row["duration"],
                    instructions=row["instructions"],
                    prescription=Prescription.objects.get(id=row["prescription"]),
                    disease=Disease.objects.filter(id=row["disease"]).first(),
                    quantity=row["quantity"],
                    drug=DrugMaster.objects.get(id=row["drug"])
                )

        self.stdout.write(self.style.SUCCESS("Data Imported Successfully 🚀"))