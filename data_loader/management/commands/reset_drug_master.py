import random
from django.core.management.base import BaseCommand
from inventory.models import DrugMaster
from core.models import Clinic


# ── Complete drug catalog — 30 drugs across 8 disease categories ──────────────
DRUG_CATALOG = [
    # Antibiotics
    {'drug_name': 'Amoxicillin',     'generic_name': 'Amoxicillin trihydrate',
     'strengths': ['250mg', '500mg'], 'dosages': ['Tablet', 'Capsule', 'Syrup'],
     'base_stock': (200, 800), 'category': 'antibiotic'},

    {'drug_name': 'Azithromycin',    'generic_name': 'Azithromycin dihydrate',
     'strengths': ['250mg', '500mg'], 'dosages': ['Tablet', 'Capsule'],
     'base_stock': (100, 400), 'category': 'antibiotic'},

    {'drug_name': 'Ciprofloxacin',   'generic_name': 'Ciprofloxacin hydrochloride',
     'strengths': ['250mg', '500mg'], 'dosages': ['Tablet', 'Injection'],
     'base_stock': (100, 350), 'category': 'antibiotic'},

    {'drug_name': 'Doxycycline',     'generic_name': 'Doxycycline hyclate',
     'strengths': ['100mg'],          'dosages': ['Tablet', 'Capsule'],
     'base_stock': (100, 300), 'category': 'antibiotic'},

    # Analgesics / Antipyretics
    {'drug_name': 'Paracetamol',     'generic_name': 'Acetaminophen',
     'strengths': ['250mg', '500mg', '650mg'], 'dosages': ['Tablet', 'Syrup', 'Injection'],
     'base_stock': (300, 1200), 'category': 'analgesic'},

    {'drug_name': 'Ibuprofen',       'generic_name': 'Ibuprofen',
     'strengths': ['200mg', '400mg', '600mg'], 'dosages': ['Tablet', 'Syrup', 'Capsule'],
     'base_stock': (200, 900), 'category': 'analgesic'},

    {'drug_name': 'Diclofenac',      'generic_name': 'Diclofenac sodium',
     'strengths': ['25mg', '50mg'],   'dosages': ['Tablet', 'Injection', 'Gel'],
     'base_stock': (150, 500), 'category': 'analgesic'},

    {'drug_name': 'Aspirin',         'generic_name': 'Acetylsalicylic acid',
     'strengths': ['75mg', '150mg', '325mg'], 'dosages': ['Tablet'],
     'base_stock': (200, 700), 'category': 'analgesic'},

    # Antihistamines / Allergy
    {'drug_name': 'Cetirizine',      'generic_name': 'Cetirizine hydrochloride',
     'strengths': ['5mg', '10mg'],    'dosages': ['Tablet', 'Syrup'],
     'base_stock': (150, 600), 'category': 'antihistamine'},

    {'drug_name': 'Chlorpheniramine','generic_name': 'Chlorpheniramine maleate',
     'strengths': ['2mg', '4mg'],     'dosages': ['Tablet', 'Syrup'],
     'base_stock': (100, 350), 'category': 'antihistamine'},

    {'drug_name': 'Montelukast',     'generic_name': 'Montelukast sodium',
     'strengths': ['4mg', '10mg'],    'dosages': ['Tablet', 'Chewable'],
     'base_stock': (80, 300), 'category': 'antihistamine'},

    # Diabetes
    {'drug_name': 'Metformin',       'generic_name': 'Metformin hydrochloride',
     'strengths': ['500mg', '850mg', '1000mg'], 'dosages': ['Tablet'],
     'base_stock': (200, 800), 'category': 'antidiabetic'},

    {'drug_name': 'Glibenclamide',   'generic_name': 'Glibenclamide',
     'strengths': ['2.5mg', '5mg'],   'dosages': ['Tablet'],
     'base_stock': (100, 400), 'category': 'antidiabetic'},

    {'drug_name': 'Glimepiride',     'generic_name': 'Glimepiride',
     'strengths': ['1mg', '2mg', '3mg'], 'dosages': ['Tablet'],
     'base_stock': (80, 300), 'category': 'antidiabetic'},

    {'drug_name': 'Insulin (Regular)','generic_name': 'Human insulin',
     'strengths': ['40 IU/ml', '100 IU/ml'], 'dosages': ['Injection'],
     'base_stock': (50, 200), 'category': 'antidiabetic'},

    # Hypertension / Cardiac
    {'drug_name': 'Amlodipine',      'generic_name': 'Amlodipine besylate',
     'strengths': ['2.5mg', '5mg', '10mg'], 'dosages': ['Tablet'],
     'base_stock': (150, 600), 'category': 'antihypertensive'},

    {'drug_name': 'Atenolol',        'generic_name': 'Atenolol',
     'strengths': ['25mg', '50mg', '100mg'], 'dosages': ['Tablet'],
     'base_stock': (100, 450), 'category': 'antihypertensive'},

    {'drug_name': 'Losartan',        'generic_name': 'Losartan potassium',
     'strengths': ['25mg', '50mg', '100mg'], 'dosages': ['Tablet'],
     'base_stock': (100, 400), 'category': 'antihypertensive'},

    {'drug_name': 'Enalapril',       'generic_name': 'Enalapril maleate',
     'strengths': ['2.5mg', '5mg', '10mg'], 'dosages': ['Tablet'],
     'base_stock': (80, 350), 'category': 'antihypertensive'},

    # Respiratory / Asthma
    {'drug_name': 'Salbutamol',      'generic_name': 'Albuterol sulfate',
     'strengths': ['2mg', '4mg'],     'dosages': ['Tablet', 'Syrup', 'Inhaler'],
     'base_stock': (100, 400), 'category': 'bronchodilator'},

    {'drug_name': 'Prednisolone',    'generic_name': 'Prednisolone',
     'strengths': ['5mg', '10mg', '20mg'], 'dosages': ['Tablet', 'Syrup'],
     'base_stock': (100, 350), 'category': 'corticosteroid'},

    {'drug_name': 'Theophylline',    'generic_name': 'Theophylline anhydrous',
     'strengths': ['100mg', '200mg'], 'dosages': ['Tablet', 'Capsule'],
     'base_stock': (80, 300), 'category': 'bronchodilator'},

    # GI / Gastric
    {'drug_name': 'Omeprazole',      'generic_name': 'Omeprazole magnesium',
     'strengths': ['10mg', '20mg', '40mg'], 'dosages': ['Capsule', 'Tablet'],
     'base_stock': (150, 600), 'category': 'antacid'},

    {'drug_name': 'Ranitidine',      'generic_name': 'Ranitidine hydrochloride',
     'strengths': ['75mg', '150mg', '300mg'], 'dosages': ['Tablet', 'Syrup'],
     'base_stock': (100, 400), 'category': 'antacid'},

    {'drug_name': 'Domperidone',     'generic_name': 'Domperidone',
     'strengths': ['5mg', '10mg'],    'dosages': ['Tablet', 'Syrup'],
     'base_stock': (100, 350), 'category': 'antiemetic'},

    # Vitamins / Supplements
    {'drug_name': 'Vitamin C',       'generic_name': 'Ascorbic acid',
     'strengths': ['250mg', '500mg', '1000mg'], 'dosages': ['Tablet', 'Syrup'],
     'base_stock': (200, 800), 'category': 'vitamin'},

    {'drug_name': 'Vitamin D3',      'generic_name': 'Cholecalciferol',
     'strengths': ['400IU', '1000IU', '2000IU'], 'dosages': ['Tablet', 'Capsule', 'Drops'],
     'base_stock': (100, 500), 'category': 'vitamin'},

    {'drug_name': 'Zinc Sulphate',   'generic_name': 'Zinc sulfate monohydrate',
     'strengths': ['10mg', '20mg'],   'dosages': ['Tablet', 'Syrup'],
     'base_stock': (100, 400), 'category': 'mineral'},

    # ORS / Hydration (critical for Tamil Nadu summer)
    {'drug_name': 'ORS',             'generic_name': 'Oral Rehydration Salts',
     'strengths': ['21g sachet'],     'dosages': ['Sachet'],
     'base_stock': (300, 1500), 'category': 'hydration'},

    # Antimalarial / Dengue support
    {'drug_name': 'Chloroquine',     'generic_name': 'Chloroquine phosphate',
     'strengths': ['150mg', '250mg'], 'dosages': ['Tablet'],
     'base_stock': (100, 400), 'category': 'antimalarial'},
]


class Command(BaseCommand):
    help = 'Resets DrugMaster with realistic 30-drug catalog and proper per-clinic stock levels'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            default=False,
            help='Clear all existing DrugMaster records before inserting (default: False)'
        )
        parser.add_argument(
            '--drugs-per-clinic',
            type=int,
            default=5,
            help='Number of unique drug variants per clinic (default: 5)'
        )

    def handle(self, *args, **options):
        clear         = options['clear']
        drugs_per_clinic = options['drugs_per_clinic']

        clinics = list(Clinic.objects.all().order_by('id'))
        if not clinics:
            self.stdout.write(self.style.ERROR('No clinics found.'))
            return

        self.stdout.write(f'\nFound {len(clinics)} clinics.')
        self.stdout.write(f'Drug catalog: {len(DRUG_CATALOG)} drugs.')

        if clear:
            count = DrugMaster.objects.count()
            DrugMaster.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing DrugMaster records.'))

        self.stdout.write('\nGenerating realistic drug stock per clinic...\n')

        to_create = []
        drug_count = {}

        for clinic in clinics:
            # Each clinic gets a random selection of drug variants
            # weighted toward common drugs
            selected_drugs = random.choices(
                DRUG_CATALOG,
                weights=[3 if d['category'] in ['analgesic', 'antibiotic', 'antihypertensive', 'antidiabetic'] else 1
                         for d in DRUG_CATALOG],
                k=drugs_per_clinic
            )

            seen = set()
            for drug in selected_drugs:
                strength = random.choice(drug['strengths'])
                dosage   = random.choice(drug['dosages'])
                key = (drug['drug_name'], strength, dosage, clinic.id)

                if key in seen:
                    continue
                seen.add(key)

                # Realistic per-clinic stock
                # Large clinics (low ID = synthetic early ones) get more stock
                min_stock, max_stock = drug['base_stock']

                # Vary stock — some clinics well-stocked, some low
                stock_tier = random.choices(
                    ['well_stocked', 'normal', 'low', 'critical'],
                    weights=[20, 50, 20, 10],
                    k=1
                )[0]

                if stock_tier == 'well_stocked':
                    stock = random.randint(max_stock // 2, max_stock)
                elif stock_tier == 'normal':
                    stock = random.randint(min_stock, max_stock // 2)
                elif stock_tier == 'low':
                    stock = random.randint(10, min_stock - 1)
                else:  # critical
                    stock = random.randint(0, 9)

                to_create.append(DrugMaster(
                    drug_name=drug['drug_name'],
                    generic_name=drug['generic_name'],
                    drug_strength=strength,
                    dosage_type=dosage,
                    current_stock=stock,
                    clinic=clinic,
                ))

                drug_count[drug['drug_name']] = drug_count.get(drug['drug_name'], 0) + 1

            # Batch insert every 2000
            if len(to_create) >= 2000:
                DrugMaster.objects.bulk_create(to_create)
                self.stdout.write(f'  Inserted {DrugMaster.objects.count()} records so far...')
                to_create = []

        # Final batch
        if to_create:
            DrugMaster.objects.bulk_create(to_create)

        total = DrugMaster.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✓ Done — {total} DrugMaster records created\n'))

        self.stdout.write('Drug distribution:')
        for name, count in sorted(drug_count.items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {name:<25} {count:>6} rows')

        # Stock tier summary
        from django.db.models import Count as DCount
        critical = DrugMaster.objects.filter(current_stock__lte=9).count()
        low      = DrugMaster.objects.filter(current_stock__gte=10, current_stock__lt=100).count()
        normal   = DrugMaster.objects.filter(current_stock__gte=100).count()

        self.stdout.write(f'\nStock distribution:')
        self.stdout.write(f'  Critical (0–9):    {critical:>6} rows')
        self.stdout.write(f'  Low (10–99):       {low:>6} rows')
        self.stdout.write(f'  Normal (100+):     {normal:>6} rows')