import random
from datetime import date
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic


class Command(BaseCommand):
    help = 'Generates realistic daily data for all models with sanity checks (OPTIMIZED)'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, default=None, help='Date to generate data for (YYYY-MM-DD)')
        parser.add_argument('--appointments', type=int, default=30, help='Number of appointments to generate')
        parser.add_argument('--spike', type=str, default=None, help='Disease name to spike (adds extra cases)')

    def handle(self, *args, **options):
        # ── Resolve date ────────────────────────────────────────────
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            target_date = date.today()

        self.stdout.write(f'\nGenerating data for {target_date}...\n')

        # ── Load reference data ────────────────────────────────────
        clinics = list(Clinic.objects.all())
        doctors = list(Doctor.objects.all())
        patients = list(Patient.objects.all())
        diseases = list(Disease.objects.filter(is_active=True))
        drugs = list(DrugMaster.objects.all())

        if not all([clinics, doctors, patients, diseases, drugs]):
            self.stdout.write(self.style.ERROR('Missing reference data'))
            return

        # ── Pre-group by clinic for speed ──────────────────────────
        doctors_by_clinic = defaultdict(list)
        for d in doctors:
            doctors_by_clinic[d.clinic_id].append(d)

        patients_by_clinic = defaultdict(list)
        for p in patients:
            patients_by_clinic[p.clinic_id].append(p)

        drugs_by_clinic = defaultdict(list)
        for d in drugs:
            drugs_by_clinic[d.clinic_id].append(d)

        # ── Season-aware disease weights ──────────────────────────
        month = target_date.month
        season_map = {
            'Summer': [3, 4, 5, 6],
            'Monsoon': [7, 8, 9, 10],
            'Winter': [11, 12, 1, 2],
        }

        def get_weight(d):
            for season, months in season_map.items():
                if d.season == season and month in months:
                    return 3
            return 1

        disease_weights = [get_weight(d) for d in diseases]

        # ── OP number start ───────────────────────────────────────
        op_base = Appointment.objects.aggregate(max_op=Max('op_number'))['max_op'] or 'OP000000'
        try:
            op_counter = int(''.join(filter(str.isdigit, op_base))) + 1
        except Exception:
            op_counter = random.randint(100000, 999999)

        # ── Helper to bulk create & refresh only current batch ────
        def bulk_create_and_refresh(model, objs):
            if not objs:
                return []
            last_id = model.objects.order_by('-id').values_list('id', flat=True).first() or 0
            model.objects.bulk_create(objs, batch_size=500)
            return list(model.objects.filter(id__gt=last_id))

        # ── Generate appointments ──────────────────────────────────
        appt_objs = []
        appt_count = options['appointments']

        for _ in range(appt_count):
            clinic = random.choice(clinics)
            doctor = random.choice(doctors_by_clinic[clinic.id] or doctors)
            patient = random.choice(patients_by_clinic[clinic.id] or patients)
            disease = random.choices(diseases, weights=disease_weights, k=1)[0]

            hour = random.randint(8, 17)
            minute = random.choice([0, 15, 30, 45])
            appt_dt = timezone.make_aware(timezone.datetime(target_date.year, target_date.month, target_date.day, hour, minute))

            status = random.choices(['Completed', 'Scheduled', 'Cancelled'], weights=[70, 20, 10])[0]

            appt_objs.append(Appointment(
                appointment_datetime=appt_dt,
                appointment_status=status,
                disease=disease,
                clinic=clinic,
                doctor=doctor,
                patient=patient,
                op_number=f'OP{op_counter:06d}'
            ))
            op_counter += 1

        created_appts = bulk_create_and_refresh(Appointment, appt_objs)
        self.stdout.write(f'  ✓ {len(created_appts)} appointments created')

        # ── Inject spike if requested ─────────────────────────────
        if options['spike']:
            spike_matches = [d for d in diseases if options['spike'].lower() in d.name.lower()]
            if spike_matches:
                spike_dis = spike_matches[0]
                spike_count = random.randint(22, 32)
                spike_appts = []

                for _ in range(spike_count):
                    clinic = random.choice(clinics)
                    doctor = random.choice(doctors_by_clinic[clinic.id] or doctors)
                    patient = random.choice(patients_by_clinic[clinic.id] or patients)
                    hour = random.randint(8, 17)
                    appt_dt = timezone.make_aware(timezone.datetime(target_date.year, target_date.month, target_date.day, hour, random.choice([0, 15, 30, 45])))

                    spike_appts.append(Appointment(
                        appointment_datetime=appt_dt,
                        appointment_status='Completed',
                        disease=spike_dis,
                        clinic=clinic,
                        doctor=doctor,
                        patient=patient,
                        op_number=f'OP{op_counter:06d}'
                    ))
                    op_counter += 1

                created_spikes = bulk_create_and_refresh(Appointment, spike_appts)
                created_appts += created_spikes
                self.stdout.write(f'  ✓ Spike injected: {len(created_spikes)} cases')
            else:
                self.stdout.write(self.style.WARNING(f'No disease found matching "{options["spike"]}". Available diseases: {[d.name for d in diseases[:5]]}...'))

        # ── Generate prescriptions ────────────────────────────────
        prescriptions = []
        completed_appts = [a for a in created_appts if a.appointment_status == 'Completed']

        for appt in completed_appts:
            if random.random() > 0.2:
                prescriptions.append(Prescription(
                    prescription_date=target_date,
                    appointment=appt,
                    clinic=appt.clinic,
                    doctor=appt.doctor,
                    patient=appt.patient
                ))

        created_prescriptions = bulk_create_and_refresh(Prescription, prescriptions)
        self.stdout.write(f'  ✓ {len(created_prescriptions)} prescriptions created')

        # ── Generate prescription lines & update stock ───────────
        prescription_lines = []
        drug_usage = defaultdict(int)

        for prescription in created_prescriptions:
            disease = prescription.appointment.disease
            available_drugs = drugs_by_clinic[prescription.clinic_id] or drugs
            chosen_drugs = random.sample(available_drugs, min(random.randint(1, 3), len(available_drugs)))

            for drug in chosen_drugs:
                qty = random.choices([1, 2, 3], weights=[3, 2, 1])[0]
                duration_days = random.choice([3, 5, 7, 10, 14])

                prescription_lines.append(PrescriptionLine(
                    prescription=prescription,
                    prescription_date=prescription.prescription_date,
                    drug=drug,
                    disease=disease,
                    quantity=qty,
                    duration=f'{duration_days} days',
                    instructions=random.choice([
                        'Take after food', 'Take before food', 'Take with water', 'Take twice daily', 'Take at bedtime', 'Take as directed'
                    ])
                ))
                drug_usage[drug.id] += qty

        bulk_create_and_refresh(PrescriptionLine, prescription_lines)

        # ── Update drug stock ─────────────────────────────────────
        drug_objs = DrugMaster.objects.filter(id__in=drug_usage.keys())
        for d in drug_objs:
            d.current_stock = max(0, d.current_stock - drug_usage[d.id])
        DrugMaster.objects.bulk_update(drug_objs, ['current_stock'], batch_size=200)

        self.stdout.write(f'  ✓ {len(prescription_lines)} prescription lines created')

        # ── SANITY CHECK VALIDATOR ───────────────────────────────
        def sanity_check():
            if len(created_appts) > appt_count + 50:
                self.stdout.write(self.style.WARNING(
                    f'⚠ Sanity Check: Created appointments ({len(created_appts)}) exceed expected (~{appt_count + 50})'
                ))
            if len(created_prescriptions) > len(completed_appts):
                self.stdout.write(self.style.WARNING(
                    f'⚠ Sanity Check: Prescriptions ({len(created_prescriptions)}) exceed completed appointments ({len(completed_appts)})'
                ))
            if len(prescription_lines) > len(created_prescriptions) * 5:
                self.stdout.write(self.style.WARNING(
                    f'⚠ Sanity Check: Prescription lines ({len(prescription_lines)}) unusually high'
                ))

        sanity_check()

        # ── DONE ──────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done — {target_date}\n'
            f'  Appointments: {len(created_appts)}\n'
            f'  Prescriptions: {len(created_prescriptions)}\n'
            f'  Prescription lines: {len(prescription_lines)}\n'
        ))