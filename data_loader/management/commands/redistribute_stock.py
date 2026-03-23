from django.core.management.base import BaseCommand
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

            DrugMaster.objects.bulk_update(to_update, ['current_stock'])

            self.stdout.write(self.style.SUCCESS(
                f'  {drug_name}: {count} rows, each gets ~{base}, total = {sum(r.current_stock for r in to_update)}'
            ))

        self.stdout.write(self.style.SUCCESS('\nDone.\n'))
