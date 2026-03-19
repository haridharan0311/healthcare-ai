import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic


class Command(BaseCommand):
    help = 'Generates realistic daily data for all 8 models for a given date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Date to generate data for (YYYY-MM-DD). Defaults to today.'
        )
        parser.add_argument(
            '--appointments',
            type=int,
            default=30,
            help='Number of appointments to generate (default: 30)'
        )
        parser.add_argument(
            '--spike',
            type=str,
            default=None,
            help='Disease name to spike (e.g. "Flu"). Adds 25 extra cases.'
        )

    def handle(self, *args, **options):
        # ── Resolve target date ──────────────────────────────────────
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            target_date = date.today()

        self.stdout.write(f'\nGenerating data for {target_date}...\n')

        # ── Load existing reference data ─────────────────────────────
        clinics  = list(Clinic.objects.all())
        doctors  = list(Doctor.objects.select_related('clinic').all())
        patients = list(Patient.objects.select_related('clinic').all())
        diseases = list(Disease.objects.filter(is_active=True))
        drugs    = list(DrugMaster.objects.all())

        if not all([clinics, doctors, patients, diseases, drugs]):
            self.stdout.write(self.style.ERROR(
                'Missing reference data. Make sure clinics, doctors, patients, diseases and drugs exist.'
            ))
            return

        # ── Season-aware disease weights ─────────────────────────────
        month = target_date.month
        season_map = {
            'Summer':  [3, 4, 5, 6],
            'Monsoon': [7, 8, 9, 10],
            'Winter':  [11, 12, 1, 2],
        }

        def get_weight(disease):
            for season, months in season_map.items():
                if disease.season == season and month in months:
                    return 3      # in-season — 3× more likely
            return 1

        disease_weights = [get_weight(d) for d in diseases]

        # ── Generate appointments ────────────────────────────────────
        appt_count  = options['appointments']
        spike_disease = options['spike']
        created_appts = []
        op_base = Appointment.objects.aggregate(
            max_op=Max('op_number')
        )['max_op'] or 'OP000000'

        # Extract numeric part for incrementing
        try:
            op_counter = int(''.join(filter(str.isdigit, op_base))) + 1
        except Exception:
            op_counter = random.randint(100000, 999999)

        for i in range(appt_count):
            clinic  = random.choice(clinics)
            doctor  = random.choice([d for d in doctors if d.clinic_id == clinic.id] or doctors)
            patient = random.choice([p for p in patients if p.clinic_id == clinic.id] or patients)
            disease = random.choices(diseases, weights=disease_weights, k=1)[0]

            # Random time between 8am and 6pm
            hour   = random.randint(8, 17)
            minute = random.choice([0, 15, 30, 45])
            appt_dt = timezone.make_aware(
                timezone.datetime(
                    target_date.year, target_date.month, target_date.day,
                    hour, minute
                )
            )

            status = random.choices(
                ['Completed', 'Scheduled', 'Cancelled'],
                weights=[70, 20, 10],
                k=1
            )[0]

            appt = Appointment.objects.create(
                appointment_datetime=appt_dt,
                appointment_status=status,
                disease=disease,
                clinic=clinic,
                doctor=doctor,
                patient=patient,
                op_number=f'OP{op_counter:06d}'
            )
            created_appts.append(appt)
            op_counter += 1

        self.stdout.write(f'  ✓ {appt_count} appointments created')

        # ── Inject spike if requested ────────────────────────────────
        if spike_disease:
            spike_matches = [d for d in diseases
                             if spike_disease.lower() in d.name.lower()]
            if spike_matches:
                spike_dis = spike_matches[0]
                spike_count = random.randint(22, 32)
                clinic  = random.choice(clinics)
                doctor  = random.choice([d for d in doctors if d.clinic_id == clinic.id] or doctors)

                for i in range(spike_count):
                    patient = random.choice([p for p in patients if p.clinic_id == clinic.id] or patients)
                    hour    = random.randint(8, 17)
                    appt_dt = timezone.make_aware(
                        timezone.datetime(
                            target_date.year, target_date.month, target_date.day,
                            hour, random.choice([0, 15, 30, 45])
                        )
                    )
                    appt = Appointment.objects.create(
                        appointment_datetime=appt_dt,
                        appointment_status='Completed',
                        disease=spike_dis,
                        clinic=clinic,
                        doctor=doctor,
                        patient=patient,
                        op_number=f'OP{op_counter:06d}'
                    )
                    created_appts.append(appt)
                    op_counter += 1

                self.stdout.write(f'  ✓ Spike injected: {spike_count} extra {spike_dis.name} cases')
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ No disease found matching "{spike_disease}"'))

        # ── Generate prescriptions for completed appointments ────────
        completed_appts = [a for a in created_appts if a.appointment_status == 'Completed']
        created_prescriptions = []

        for appt in completed_appts:
            # 80% of completed appointments get a prescription
            if random.random() > 0.20:
                prescription = Prescription.objects.create(
                    prescription_date=target_date,
                    appointment=appt,
                    clinic=appt.clinic,
                    doctor=appt.doctor,
                    patient=appt.patient,
                )
                created_prescriptions.append((prescription, appt.disease))

        self.stdout.write(f'  ✓ {len(created_prescriptions)} prescriptions created')

        # ── Generate prescription lines ──────────────────────────────
        line_count = 0
        clinic_drugs = {c.id: [d for d in drugs if d.clinic_id == c.id] for c in clinics}

        for prescription, disease in created_prescriptions:
            available_drugs = (
                clinic_drugs.get(prescription.clinic_id, []) or drugs
            )
            # 1 to 3 drugs per prescription
            num_drugs = random.randint(1, 3)
            chosen_drugs = random.sample(
                available_drugs,
                min(num_drugs, len(available_drugs))
            )

            for drug in chosen_drugs:
                quantity = random.choice([1, 1, 1, 2, 2, 3])   # weighted toward 1-2
                duration_days = random.choice([3, 5, 7, 10, 14])

                PrescriptionLine.objects.create(
                    prescription=prescription,
                    drug=drug,
                    disease=disease,
                    quantity=quantity,
                    duration=f'{duration_days} days',
                    instructions=random.choice([
                        'Take after food',
                        'Take before food',
                        'Take with water',
                        'Take twice daily',
                        'Take at bedtime',
                        'Take as directed',
                    ])
                )
                line_count += 1

                # Update drug stock (consume)
                if drug.current_stock > 0:
                    DrugMaster.objects.filter(id=drug.id).update(
                        current_stock=max(0, drug.current_stock - quantity)
                    )

        self.stdout.write(f'  ✓ {line_count} prescription lines created')

        # ── Summary ──────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done — {target_date} data generation complete\n'
            f'  Appointments:       {appt_count}\n'
            f'  Prescriptions:      {len(created_prescriptions)}\n'
            f'  Prescription lines: {line_count}\n'
        ))
