# Data Loader Documentation

All management commands live in:
  data_loader/management/commands/

Run any command from the project root with virtual environment activated:
  python manage.py <command_name> [options]

---

## Commands Overview

| Command                        | Purpose                                              | When to run         |
|--------------------------------|------------------------------------------------------|---------------------|
| import_data                    | Import 8 CSV files into DB                          | Once on fresh setup |
| update_clinic_addresses        | Set Tamil Nadu addresses for all 20k clinics        | Once                |
| reset_drug_master              | Clear drugs and create 30-drug catalog              | Once                |
| redistribute_stock             | Evenly distribute stock across all drug rows        | After reset_drug    |
| regenerate_prescription_lines  | Rebuild prescription lines after drug master reset  | After reset_drug    |
| inject_spike                   | Inject a demo disease spike for dashboard demo      | As needed           |
| generate_daily_data            | Add daily appointments, prescriptions, lines        | Daily (automated)   |

---

## 1. import_data

Imports all 8 source CSV files from the data/ folder into the database.
Must be run first, before any other command.

```bash
python manage.py import_data
```

CSV files required in data/:
  appointment.csv, clinic.csv, disease.csv, doctor.csv,
  drugmaster.csv, patient.csv, prescription.csv, prescriptionline.csv

Each file: 20,000 rows
Total records imported: ~160,000

---

## 2. update_clinic_addresses

Replaces all clinic addresses with realistic Tamil Nadu addresses.
Covers all 38 districts proportionally — larger cities get more clinics.

Generated address format:
  No.247/B, 12, Kamaraj Main Road, Avinashi Road, Coimbatore,
  Coimbatore, Tamil Nadu - 641003. Ph: 0422-6483921

The district is always the 5th comma-separated segment.
All analytics district filtering depends on this exact format.

```bash
# Update all 20,000 clinics across all 38 districts
python manage.py update_clinic_addresses

# Update with larger batch size (faster)
python manage.py update_clinic_addresses --batch-size 1000

# Update only one specific district
python manage.py update_clinic_addresses --district Chennai
python manage.py update_clinic_addresses --district Coimbatore
python manage.py update_clinic_addresses --district Madurai
python manage.py update_clinic_addresses --district Salem
```

Arguments:
  --batch-size   integer   500    Records per DB bulk_update call
  --district     string    all    If given, only updates clinics in that district

District weight distribution (higher weight = more clinics assigned):
  Chennai: 15, Coimbatore: 10, Madurai: 8, Salem: 6,
  Tiruchirappalli: 6, Vellore: 5, Tiruppur: 5, Erode: 4,
  Thanjavur: 4, all others: 2

All 38 districts covered:
  Chennai, Coimbatore, Madurai, Salem, Tiruchirappalli, Tirunelveli,
  Vellore, Erode, Thanjavur, Tiruppur, Kancheepuram, Dindigul,
  Villupuram, Cuddalore, Nagapattinam, Pudukottai, Ramanathapuram,
  Thoothukudi, Virudhunagar, Sivaganga, Theni, Krishnagiri, Dharmapuri,
  Tiruvannamalai, Namakkal, Nilgiris, Karur, Ariyalur, Perambalur,
  Tiruvarur, Kallakurichi, Tenkasi, Ranipet, Chengalpet,
  Mayiladuthurai, Tirupathur

---

## 3. reset_drug_master

Clears existing DrugMaster data and creates a realistic 30-drug catalog.
Each clinic gets a random weighted selection of drug variants.

WARNING: Running with --clear triggers CASCADE deletion of all PrescriptionLine records
because PrescriptionLine has on_delete=CASCADE to DrugMaster.
Always run regenerate_prescription_lines after this command.

30-drug catalog by category:

  Antibiotics (4):
    Amoxicillin 250/500mg — Tablet, Capsule, Syrup
    Azithromycin 250/500mg — Tablet, Capsule
    Ciprofloxacin 250/500mg — Tablet, Injection
    Doxycycline 100mg — Tablet, Capsule

  Analgesics / Antipyretics (4):
    Paracetamol 250/500/650mg — Tablet, Syrup, Injection
    Ibuprofen 200/400/600mg — Tablet, Syrup, Capsule
    Diclofenac 25/50mg — Tablet, Injection, Gel
    Aspirin 75/150/325mg — Tablet

  Antihistamines / Allergy (3):
    Cetirizine 5/10mg — Tablet, Syrup
    Chlorpheniramine 2/4mg — Tablet, Syrup
    Montelukast 4/10mg — Tablet, Chewable

  Antidiabetics (4):
    Metformin 500/850/1000mg — Tablet
    Glibenclamide 2.5/5mg — Tablet
    Glimepiride 1/2/3mg — Tablet
    Insulin (Regular) 40/100 IU/ml — Injection

  Antihypertensives (4):
    Amlodipine 2.5/5/10mg — Tablet
    Atenolol 25/50/100mg — Tablet
    Losartan 25/50/100mg — Tablet
    Enalapril 2.5/5/10mg — Tablet

  Respiratory (3):
    Salbutamol 2/4mg — Tablet, Syrup, Inhaler
    Prednisolone 5/10/20mg — Tablet, Syrup
    Theophylline 100/200mg — Tablet, Capsule

  GI / Gastric (3):
    Omeprazole 10/20/40mg — Capsule, Tablet
    Ranitidine 75/150/300mg — Tablet, Syrup
    Domperidone 5/10mg — Tablet, Syrup

  Vitamins / Supplements (3):
    Vitamin C 250/500/1000mg — Tablet, Syrup
    Vitamin D3 400/1000/2000 IU — Tablet, Capsule, Drops
    Zinc Sulphate 10/20mg — Tablet, Syrup

  Hydration (1):
    ORS 21g sachet — Sachet

  Antimalarial (1):
    Chloroquine 150/250mg — Tablet

```bash
# Append new drugs (does not delete existing)
python manage.py reset_drug_master

# Clear all existing and create fresh (recommended)
python manage.py reset_drug_master --clear

# Control drug variants per clinic
python manage.py reset_drug_master --clear --drugs-per-clinic 5    # default
python manage.py reset_drug_master --clear --drugs-per-clinic 8    # more variety
python manage.py reset_drug_master --clear --drugs-per-clinic 3    # lighter dataset
```

Arguments:
  --clear              flag     false   Delete all existing DrugMaster records first
  --drugs-per-clinic   integer  5       Number of drug variants assigned per clinic

Stock tier distribution applied per row:
  well_stocked (20%)   stock between max/2 and max
  normal (50%)         stock between min and max/2
  low (20%)            stock between 10 and min-1
  critical (10%)       stock between 0 and 9

After running, also run:
  python manage.py redistribute_stock
  python manage.py regenerate_prescription_lines

---

## 4. redistribute_stock

After reset_drug_master, the dashboard stock_map sums all rows per drug name.
With ~3,300 rows per drug, even small per-row stock totals to millions.
This command overrides stock to match defined target totals.

Target total stock per drug (system-wide):
  Paracetamol:   120
  Ibuprofen:   8,500
  Amoxicillin: 5,000
  Metformin:   2,000
  Aspirin:     4,000
  Cetirizine:    320

```bash
python manage.py redistribute_stock
```

No arguments. Always run after reset_drug_master.

Expected output:
  Paracetamol: 3340 rows, each gets ~0, total = 120
  Ibuprofen:   3349 rows, each gets ~2, total = 8500
  Amoxicillin: 3359 rows, each gets ~1, total = 5000
  Metformin:   3273 rows, each gets ~0, total = 2000
  Aspirin:     3328 rows, each gets ~1, total = 4000
  Cetirizine:  3351 rows, each gets ~0, total = 320

---

## 5. regenerate_prescription_lines

Rebuilds PrescriptionLine records for all existing Prescriptions.
Run this after reset_drug_master --clear because the CASCADE delete removes lines.

```bash
python manage.py regenerate_prescription_lines

# Larger batch = faster but more memory
python manage.py regenerate_prescription_lines --batch-size 2000
```

Arguments:
  --batch-size   integer   1000   Records per bulk_create call

What it creates per prescription:
  1 to 3 drug lines
  Random drug from the clinic's DrugMaster records
  Random disease from active diseases
  Quantity: weighted toward 1-2 units
  Duration: 3, 5, 7, 10, or 14 days
  Instructions: one of 8 standard phrases

Expected output:
  Found 142,000 prescriptions.
  Existing prescription lines: 0

  1000 lines created (500/142000 prescriptions processed)...
  2000 lines created (1000/142000 prescriptions processed)...
  ...

  Prescriptions processed: 142,000
  Prescription lines created: 284,000
  Average lines per prescription: 2.0

---

## 6. inject_spike

Injects a realistic disease spike into the latest date in the DB.
Creates 22-32 extra appointments for the chosen disease on that date.
Also creates 2-4 normal baseline appointments on the previous day.

```bash
python manage.py inject_spike
```

No arguments. The command auto-selects the first Monsoon disease.
To inject a different disease, edit inject_spike.py:
  Change: Disease.objects.filter(is_active=True, season='Monsoon').first()
  To:     Disease.objects.filter(name__icontains='Flu', is_active=True).first()

What is created:
  2-4 appointments on previous date (normal baseline)
  25-35 appointments on latest date (spike)
  Uses existing clinic, doctor, patient records only

After running, spike-alerts API returns is_spike: true for that disease.

---

## 7. generate_daily_data

The main daily automation command.
Creates realistic appointments, prescriptions, and prescription lines for any date.
Uses season-aware disease weights — in-season diseases appear 3x more often.

Records created per default run (30 appointments):
  Appointments:        30     across random clinics, doctors, patients
  Prescriptions:      ~21     70% completed x 80% get a prescription
  Prescription lines: ~42     avg 2 drugs per prescription
  Stock updated:      yes     current_stock reduced by quantity prescribed

```bash
# ── Basic usage ───────────────────────────────────────────────

# Generate data for TODAY (30 appointments by default)
python manage.py generate_daily_data

# Generate for a specific date
python manage.py generate_daily_data --date 2026-03-25

# ── Control appointment count ─────────────────────────────────

python manage.py generate_daily_data --appointments 15    # light day
python manage.py generate_daily_data --appointments 30    # normal day (default)
python manage.py generate_daily_data --appointments 60    # busy day

# ── Spike injection ───────────────────────────────────────────

python manage.py generate_daily_data --spike Flu
python manage.py generate_daily_data --spike COVID-19
python manage.py generate_daily_data --spike Diabetes
python manage.py generate_daily_data --spike Asthma
python manage.py generate_daily_data --spike Hypertension

# ── Combine all options ───────────────────────────────────────

python manage.py generate_daily_data --date 2026-03-25 --appointments 50 --spike Flu
python manage.py generate_daily_data --date 2026-03-26 --appointments 15 --spike COVID-19
```

Arguments:
  --date           YYYY-MM-DD    today    Date to generate data for
  --appointments   integer       30       Number of appointments to create
  --spike          string        none     Disease name to spike (22-32 extra cases)

Important notes:
  Running twice on the same date APPENDS more data — it does not replace.
  The --spike name is fuzzy matched: --spike Flu matches "Flu 2", "Flu 14" etc.
  Use canonical type names: Flu, COVID-19, Diabetes, Asthma,
    Hypertension, Migraine, Allergy, Arthritis

---

## Bulk generation — next 7 days (copy-paste ready)

```bash
python manage.py generate_daily_data --date 2026-03-24 --appointments 32
python manage.py generate_daily_data --date 2026-03-25 --appointments 28 --spike Flu
python manage.py generate_daily_data --date 2026-03-26 --appointments 35
python manage.py generate_daily_data --date 2026-03-27 --appointments 30 --spike Diabetes
python manage.py generate_daily_data --date 2026-03-28 --appointments 40
python manage.py generate_daily_data --date 2026-03-29 --appointments 25 --spike COVID-19
python manage.py generate_daily_data --date 2026-03-30 --appointments 33
```

---

## Windows Task Scheduler Setup

Automate daily data generation to run every morning at 8am.

Step 1 — Create run_daily.bat in the project root:

  @echo off
  cd E:\technospice\project\healthcare_ai
  call .venv\Scripts\activate
  python manage.py generate_daily_data --appointments 30

Step 2 — Open Task Scheduler:
  Win + R → taskschd.msc → Enter

Step 3 — Create Basic Task:
  Name:     Healthcare AI Daily Data
  Trigger:  Daily at 08:00 AM
  Action:   Start a program → browse to run_daily.bat
  Finish

Every morning at 8am: 30 appointments, ~21 prescriptions, ~42 lines generated automatically.

---

## Complete fresh-install sequence

```bash
python manage.py migrate
python manage.py import_data
python manage.py update_clinic_addresses
python manage.py reset_drug_master --clear --drugs-per-clinic 5
python manage.py redistribute_stock
python manage.py regenerate_prescription_lines
python manage.py inject_spike
python manage.py generate_daily_data --appointments 30
python manage.py runserver
```

---

## Model write/read roles

  Master data — READ only (already exists from import):
    Clinic, Doctor, Patient, Disease

  Updated by reset commands:
    DrugMaster.current_stock — set by reset_drug_master, redistribute_stock

  Transactional data — WRITE by generate_daily_data:
    Appointment      — N created per run based on --appointments
    Prescription     — ~80% of completed appointments get one
    PrescriptionLine — 1 to 3 per prescription

  Cascade relationship:
    DrugMaster (DELETE) → PrescriptionLine (CASCADE DELETE)
    Always run regenerate_prescription_lines after reset_drug_master --clear
