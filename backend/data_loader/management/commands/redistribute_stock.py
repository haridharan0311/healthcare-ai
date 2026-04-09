import time
from django.core.management.base import BaseCommand
from django.db.utils import OperationalError
from inventory.models import DrugMaster


TOTAL_STOCK = {
    'Paracetamol': 120,
    'Ibuprofen':   8500,
    'Amoxicillin': 5000,
    'Metformin':   2000,
    'Aspirin':     4000,
    'Cetirizine':  320,
}


class Command(BaseCommand):
    help = 'Redistributes stock evenly across all DrugMaster rows per drug name'

    def bulk_update_with_retry(self, objects, fields, max_retries=3):
        """Update objects with retry logic for deadlocks and lock timeouts."""
        for attempt in range(max_retries):
            try:
                DrugMaster.objects.bulk_update(objects, fields)
                return True
            except OperationalError as e:
                error_code = e.args[0] if e.args else 0
                # Retry on: 1205 (lock timeout) and 1213 (deadlock)
                if error_code in (1205, 1213) and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.stdout.write(
                        self.style.WARNING(
                            f'    Database lock issue (code {error_code}), '
                            f'retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})'
                        )
                    )
                    time.sleep(wait_time)
                else:
                    raise

    def handle(self, *args, **options):
        self.stdout.write('\nRedistributing stock across all DrugMaster rows...\n')

        for drug_name, total in TOTAL_STOCK.items():
            rows = list(DrugMaster.objects.filter(drug_name=drug_name).order_by('id'))
            count = len(rows)

            if count == 0:
                self.stdout.write(f'  {drug_name}: no rows found, skipping')
                continue

            base      = total // count
            remainder = total % count

            to_update = []
            for i, row in enumerate(rows):
                row.current_stock = base + (1 if i < remainder else 0)
                to_update.append(row)

            self.bulk_update_with_retry(to_update, ['current_stock'])

            self.stdout.write(self.style.SUCCESS(
                f'  {drug_name}: {count} rows, each gets ~{base}, total = {sum(r.current_stock for r in to_update)}'
            ))

        self.stdout.write(self.style.SUCCESS('\nDone.\n'))
