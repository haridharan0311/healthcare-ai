from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic


class Command(BaseCommand):
    help = 'Injects a realistic disease spike into the last 2 days for demo purposes'

    def handle(self, *args, **options):
        # Get the latest appointment date in DB
        from django.db.models import Max
        latest = Appointment.objects.aggregate(
            latest=Max('appointment_datetime')
        )['latest']

        if not latest:
            self.stdout.write(self.style.ERROR('No appointments found in DB'))
            return

        spike_date = latest.date()
        prev_date  = spike_date - timedelta(days=1)

        # Pick Dengue or the first monsoon disease available
        disease = (
            Disease.objects
            .filter(is_active=True, season='Monsoon')
            .first()
        )
        if not disease:
            disease = Disease.objects.filter(is_active=True).first()

        if not disease:
            self.stdout.write(self.style.ERROR('No active diseases found'))
            return

        # Use any existing clinic/doctor/patient to keep FK constraints valid
        clinic  = Clinic.objects.first()
        doctor  = Doctor.objects.filter(clinic=clinic).first()
        patients = list(Patient.objects.filter(clinic=clinic)[:30])

        if not clinic or not doctor or not patients:
            self.stdout.write(self.style.ERROR('Missing clinic/doctor/patients'))
            return

        # Normal day: 2–4 cases on prev_date (matches existing pattern)
        normal_count = random.randint(2, 4)
        for i in range(normal_count):
            patient = random.choice(patients)
            Appointment.objects.create(
                appointment_datetime=timezone.make_aware(
                    timezone.datetime.combine(prev_date, timezone.datetime.min.time())
                    + timedelta(hours=random.randint(8, 17))
                ),
                appointment_status='completed',
                disease=disease,
                clinic=clinic,
                doctor=doctor,
                patient=patient,
                op_number=f'SPIKE-PREV-{i:04d}'
            )

        # Spike day: 25–35 cases on spike_date (well above mean + 2×std)
        spike_count = random.randint(25, 35)
        for i in range(spike_count):
            patient = random.choice(patients)
            Appointment.objects.create(
                appointment_datetime=timezone.make_aware(
                    timezone.datetime.combine(spike_date, timezone.datetime.min.time())
                    + timedelta(hours=random.randint(8, 17))
                ),
                appointment_status='completed',
                disease=disease,
                clinic=clinic,
                doctor=doctor,
                patient=patient,
                op_number=f'SPIKE-{i:04d}'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Injected spike: {spike_count} cases of "{disease.name}" '
            f'on {spike_date} (normal baseline ~{normal_count}/day)'
        ))

