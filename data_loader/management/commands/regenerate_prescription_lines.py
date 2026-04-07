import random
import time
from django.core.management.base import BaseCommand
from django.db.utils import OperationalError
from inventory.models import Prescription, PrescriptionLine, DrugMaster
from core.models import Clinic


class Command(BaseCommand):
    help = 'Regenerates PrescriptionLine records for all existing Prescriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for bulk_create (default: 500)'
        )

    def bulk_create_with_retry(self, objects, max_retries=3):
        """Insert objects with retry logic for deadlocks."""
        for attempt in range(max_retries):
            try:
                PrescriptionLine.objects.bulk_create(objects)
                return True
            except OperationalError as e:
                if '1213' in str(e) and attempt < max_retries - 1:  # Deadlock error code
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.stdout.write(
                        self.style.WARNING(
                            f'    Deadlock detected, retrying in {wait_time}s... '
                            f'(attempt {attempt + 1}/{max_retries})'
                        )
                    )
                    time.sleep(wait_time)
                else:
                    raise

    def handle(self, *args, **options):
        batch_size = options['batch_size']

        prescriptions = Prescription.objects.select_related(
            'clinic', 'patient', 'doctor'
        ).all()

        total_rx = prescriptions.count()
        if total_rx == 0:
            self.stdout.write(self.style.ERROR('No prescriptions found.'))
            return

        existing_lines = PrescriptionLine.objects.count()
        self.stdout.write(f'\nFound {total_rx} prescriptions.')
        self.stdout.write(f'Existing prescription lines: {existing_lines}')

        # Build clinic → drugs map for fast lookup
        all_drugs = list(DrugMaster.objects.select_related('clinic').all())
        if not all_drugs:
            self.stdout.write(self.style.ERROR('No DrugMaster records found. Run reset_drug_master first.'))
            return

        clinic_drugs = {}
        for drug in all_drugs:
            cid = drug.clinic_id
            if cid not in clinic_drugs:
                clinic_drugs[cid] = []
            clinic_drugs[cid].append(drug)

        # Get active diseases for prescription lines
        from analytics.models import Disease
        diseases = list(Disease.objects.filter(is_active=True))
        if not diseases:
            self.stdout.write(self.style.ERROR('No active diseases found.'))
            return

        INSTRUCTIONS = [
            'Take after food',
            'Take before food',
            'Take with water',
            'Take twice daily',
            'Take at bedtime',
            'Take as directed',
            'Take once daily in the morning',
            'Take with warm water',
        ]
        DURATIONS = ['3 days', '5 days', '7 days', '10 days', '14 days']

        to_create = []
        created_count = 0
        processed = 0

        self.stdout.write('\nGenerating prescription lines...\n')

        for prescription in prescriptions.iterator(chunk_size=500):
            # Get drugs available at this prescription's clinic
            available_drugs = clinic_drugs.get(prescription.clinic_id, [])
            if not available_drugs:
                # Fallback: use any drug
                available_drugs = random.sample(all_drugs, min(3, len(all_drugs)))

            # 1 to 3 drugs per prescription
            num_drugs = random.randint(1, 3)
            chosen_drugs = random.sample(
                available_drugs,
                min(num_drugs, len(available_drugs))
            )

            # Pick a disease for this prescription line
            disease = random.choice(diseases)

            for drug in chosen_drugs:
                to_create.append(PrescriptionLine(
                    prescription=prescription,
                    prescription_date=prescription.prescription_date,
                    drug=drug,
                    disease=disease,
                    quantity=random.choice([1, 1, 2, 2, 3]),
                    duration=random.choice(DURATIONS),
                    instructions=random.choice(INSTRUCTIONS),
                ))

            processed += 1

            # Batch insert with deadlock retry logic
            if len(to_create) >= batch_size:
                self.bulk_create_with_retry(to_create)
                created_count += len(to_create)
                to_create = []
                self.stdout.write(
                    f'  {created_count} lines created '
                    f'({processed}/{total_rx} prescriptions processed)...'
                )

        # Final batch
        if to_create:
            self.bulk_create_with_retry(to_create)
            created_count += len(to_create)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done\n'
            f'  Prescriptions processed: {processed}\n'
            f'  Prescription lines created: {created_count}\n'
            f'  Average lines per prescription: {created_count / processed:.1f}\n'
        ))