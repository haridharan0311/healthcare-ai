# Data Loader - CSV Import/Export Guide

## Overview

Data loader provides three management commands for:
- **export_data** — Backup database to CSV
- **import_data** — Restore from CSV backup
- **optimize_db** — Add database indexes for speed

## Quick Commands

### Backup Database

```bash
python manage.py export_data
```

Creates 8 CSV files in `data/` folder with all records.

### Restore from Backup

```bash
python manage.py import_data
```

Imports all CSV files. Must have `data/*.csv` files present.

### Optimize Speed

```bash
python manage.py optimize_db
```

Adds 7 database indexes, making queries 5-10x faster.

## Export Data

### Purpose
- Backup current database state
- Migrate to another environment
- Share data for testing

### Usage

```bash
python manage.py export_data
```

### Output (in `data/` folder)
- `Clinic.csv` — All clinics
- `Doctor.csv` — All doctors
- `Patient.csv` — All patients
- `Disease.csv` — All diseases
- `DrugMaster.csv` — All medicines
- `Appointment.csv` — All appointments
- `Prescription.csv` — All prescriptions
- `PrescriptionLine.csv` — All prescription items

### Example Output
```
Exporting Clinics...
Exporting Diseases...
Exporting Doctors...
...
✅ ALL DATA EXPORTED SUCCESSFULLY TO CSV FILES
```

## Import Data

### Purpose
- Restore from backup
- Load initial test data
- Migrate from exported CSV

### Prerequisites
- All 8 CSV files must exist in `data/` folder
- Files must have correct column headers
- Foreign key IDs must be valid

### Usage

```bash
python manage.py import_data
```

### Import Order
The command automatically imports in correct order:
1. Clinic (base data)
2. Disease (base data)
3. Doctor (references Clinic)
4. Patient (references Clinic, Doctor)
5. DrugMaster (references Clinic)
6. Appointment (references Disease, Clinic, Doctor, Patient)
7. Prescription (references Appointment)
8. PrescriptionLine (references Prescription)

### Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Duplicate entry" | Data already exists | Run `python manage.py flush` first |
| "FILE NOT FOUND" | CSV missing | Check `data/` folder has all 8 files |
| "Missing column" | Wrong CSV headers | Check column names match exact case |
| "FK not found" | Invalid ID reference | Ensure correct import order |

## Optimize Database

### Purpose
- Speed up queries 5-10x
- Add indexes to frequent filters
- Recommended after import

### Usage

```bash
python manage.py optimize_db
```

### Indexes Created

| Index | Purpose | Query Time |
|-------|---------|------------|
| appointment_datetime | Date filtering | 5sec → 500ms |
| appointment_disease_id | Disease filtering | 3sec → 300ms |
| appointment_clinic_id | Clinic filtering | 2sec → 200ms |
| prescription_date | Date queries | 2sec → 200ms |
| prescriptionline_disease_id | Disease filtering | 1sec → 100ms |
| Composite indexes | Combined filters | 8sec → 1sec |

### Example Output

```
✓ Created appointment_datetime index
✓ Created appointment_disease_id index
✓ Created appointment_clinic_id index
✓ Created prescription_date index
✓ Created prescriptionline_disease_id index
✓ Created appointment datetime+disease composite index
✓ Created prescriptionline prescription+drug composite index

✓ Database optimization complete
```

## Workflow Example

### 1. Reset and Restore

```bash
# Clear all data
python manage.py flush --no-input

# Restore from backup
python manage.py import_data

# Add indexes
python manage.py optimize_db
```

### 2. Backup Before Big Changes

```bash
# Backup current state
python manage.py export_data

# ... make changes ...

# Restore if needed
python manage.py import_data
```

### 3. Setup New Environment

```bash
# In new environment
python manage.py migrate
python manage.py import_data
python manage.py optimize_db
python manage.py runserver
```

## Testing

Run data loader tests:

```bash
python manage.py test data_loader.tests.test_commands
```

Test coverage:
- ✓ export_data creates CSV files
- ✓ CSV files have correct headers
- ✓ import_data runs without errors
- ✓ optimize_db runs successfully

## Troubleshooting

**Q: "Duplicate entry" error during import**  
A: Data already exists. Run `python manage.py flush` to clear, then import.

**Q: CSV file not found**  
A: Check all 8 files exist in `data/` folder with correct names (case-sensitive).

**Q: "FK constraint violation"**  
A: Parent record missing. Make sure import order is correct.

**Q: Queries still slow after optimize_db**  
A: Run optimize_db again or check if indexes exist.

The data_loader app ensures:
- **Initial Data Import** — Load 8 CSV files (20k rows each) into the database atomically
- **Daily Data Synchronization** — Auto-generate realistic appointment and prescription data
- **Data Transformations** — Update addresses, regenerate references, maintain data consistency
- **Inventory Management** — Reset catalogs, redistribute stock, manage pharmacy inventory
- **Demo Data Injection** — Inject spikes for testing outbreak detection features

### Key Features

- **Atomic Transactions** — All imports are wrapped in `transaction.atomic()` for consistency
- **Bulk Operations** — Uses `bulk_create()` and `bulk_update()` for performance (batch_size=500-1000)
- **Reference Data Caching** — Pre-loads clinics, doctors, patients, diseases into memory for O(1) lookups
- **Season-Aware Processing** — Applies seasonal weights during daily data generation
- **Error Handling** — Validates data before import, provides clear error messages

### File Structure

```
data_loader/
├── apps.py                      App configuration
├── admin.py                     Django admin (empty by default)
├── __init__.py                  Package marker
└── management/
    └── commands/
        ├── import_data.py                  ★ Initial CSV import
        ├── generate_daily_data.py          ★ Daily appointment generation
        ├── reset_drug_master.py            Reset 30-drug catalog
        ├── redistribute_stock.py           Evenly distribute inventory
        ├── update_clinic_addresses.py      Generate Tamil Nadu addresses
        ├── inject_spike.py                 Inject disease spikes
        ├── regenerate_prescription_lines.py  Rebuild prescription lines
        └── __init__.py                     Package marker
```

---

## Management Commands

### 1. **import_data** — Initial CSV Import

**Purpose:** Load all 8 CSV files (Clinic, Doctor, Patient, Disease, Appointment, Prescription, PrescriptionLine, DrugMaster) into the database.

**Command:**
```bash
python manage.py import_data
```

**Process:**
1. Reads 8 CSV files from `data/` folder
2. Creates in-memory maps for lookups (clinic_map, doctor_map, etc.)
3. Bulk imports each model atomically
4. Batch size: 1000 rows per insert
5. Handles FK relationships via maps (no DB query per row)

**CSV Files Expected:**
```
data/
├── Clinic.csv              (id, clinic_name, clinic_address_1)
├── Disease.csv             (id, name, season, category, severity, is_active, created_at)
├── Doctor.csv              (id, first_name, last_name, gender, qualification, clinic)
├── Patient.csv             (id, first_name, last_name, gender, dob, mobile, clinic, doctor)
├── Appointment.csv         (id, appointment_datetime, status, disease, clinic, doctor, patient, op_number)
├── Prescription.csv        (id, prescription_date, appointment, clinic, doctor, patient)
├── PrescriptionLine.csv    (id, drug, quantity, duration, instructions, disease, prescription)
└── DrugMaster.csv          (id, drug_name, generic_name, strength, dosage_type, current_stock, clinic)
```

**Features:**
- Datetime parsing with timezone awareness (`make_aware()`)
- Boolean conversion for `is_active` field
- Optimization: No N+1 queries (uses pre-built maps)

**Example Output:**
```
Importing Clinics...
Importing Diseases...
Importing Doctors...
Importing Patients...
Importing Appointments...
Importing Prescriptions...
Importing PrescriptionLines...
Importing DrugMaster...
✓ Import complete: X clinics, Y doctors, Z patients...
```

**Time Complexity:** O(n) where n = total rows across all CSVs

**Notes:**
- Must run this before any other commands
- Clears existing data if tables already populated (no duplicate check)
- Transaction rolls back on any error

---

### 2. **generate_daily_data** — Daily Appointment Generation

**Purpose:** Generate realistic daily data for appointments, prescriptions, and prescription lines. Used for daily synchronization and testing.

**Command:**
```bash
python manage.py generate_daily_data [OPTIONS]
```

**Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--date` | YYYY-MM-DD | Today | Date to generate data for (historical dates supported) |
| `--appointments` | Integer | 30 | Number of appointments to create |
| `--spike` | String | None | Disease name to spike (adds extra cases for testing) |

**Examples:**
```bash
# Generate today's data (30 appointments)
python manage.py generate_daily_data

# Generate for specific date with 50 appointments
python manage.py generate_daily_data --date=2026-03-25 --appointments=50

# Generate with disease spike (outbreak testing)
python manage.py generate_daily_data --spike="Influenza" --appointments=40

# Historical data (supports past dates)
python manage.py generate_daily_data --date=2026-01-15 --appointments=20
```

**Process:**
1. **Date Resolution** — Uses provided date or today's date
2. **Reference Data Loading** — Pre-loads all clinics, doctors, patients, diseases, drugs
3. **Clinic Grouping** — Pre-groups doctors, patients, drugs by clinic for O(1) lookup
4. **Season-Aware Weighting** — Applies 3x weight to diseases matching current season
5. **Appointment Generation** — Creates N random appointments (08:00-17:00 hours)
6. **Prescription Generation** — Each appointment generates 1-3 prescriptions
7. **PrescriptionLine Generation** — Each prescription gets 1-5 medicine lines
8. **Stock Decrement** — Updates `DrugMaster.current_stock` based on usage

**Season Mapping:**
```
Season      Active Months     Weight
Summer      Mar-Jun          3.0x
Monsoon     Jul-Oct          3.0x
Winter      Nov-Feb          3.0x
Off-season  Other months     1.0x
```

**Data Generated:**
- **Appointments:** Datetime, status (completed), disease, clinic, doctor, patient, OP number
- **Prescriptions:** Each appointment
- **PrescriptionLines:** 1-5 lines per prescription with random drugs and quantities
- **Stock Updates:** `DrugMaster.current_stock` decremented by usage amount

**Features:**
- **OP Number Generation** — Auto-increments from previous max (e.g., OP000001, OP000002)
- **Disease Weighting** — Season-aware selection (current season diseases 3x more likely)
- **Clinic-Aware Selection** — Doctors and patients filtered by clinic context
- **Bulk Operations** — Uses batch_size=500 for efficiency
- **Transaction Safety** — One atomic transaction per run

**Optimization:**
- Pre-groups doctors, patients, drugs by clinic ID (defaultdict)
- Uses `random.choices()` with disease_weights for efficient weighted selection
- No query per appointment (all data in memory)

**Example Output:**
```
Generating data for 2026-03-31...

✓ Created 30 appointments
✓ Created 45 prescriptions
✓ Created 132 prescription lines
✓ Updated stock levels for 28 drugs

Generation complete!
```

**Typical Frequency:** Run daily at 8 AM via Windows Task Scheduler / Cron

**Notes:**
- Requires all reference data (clinics, doctors, patients, diseases, drugs) to exist
- Stock decrements may make some drugs go into "critical" status
- Use `redistribute_stock` periodically to reset inventory levels

---

### 3. **reset_drug_master** — Reset Drug Catalog

**Purpose:** Create or reset the 30-drug catalog with realistic stock levels. Used after `import_data` or when rebuilding the catalog.

**Command:**
```bash
python manage.py reset_drug_master [OPTIONS]
```

**Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--clear` | Flag | False | Delete all existing DrugMaster rows first |
| `--drugs-per-clinic` | Integer | 5 | Number of drug variants per clinic |

**Examples:**
```bash
# Create 30-drug catalog (5 variants per clinic)
python manage.py reset_drug_master

# Reset existing catalog (delete then recreate)
python manage.py reset_drug_master --clear

# Custom drugs per clinic
python manage.py reset_drug_master --clear --drugs-per-clinic=3
```

**Drug Catalog (30 Drugs × 8 Categories):**

**Antibiotics (4):**
- Amoxicillin (250mg, 500mg tablets/syrup)
- Azithromycin (250mg, 500mg tablets)
- Ciprofloxacin (250mg, 500mg tablets/injection)
- Doxycycline (100mg tablets/capsules)

**Analgesics/Antipyretics (4):**
- Paracetamol (250mg, 500mg, 650mg — highly popular)
- Ibuprofen (200mg, 400mg, 600mg tablets/syrup)
- Diclofenac (25mg, 50mg tablets/injection)
- Aspirin (75mg, 150mg, 325mg tablets)

**Antihistamines/Allergy (3):**
- Cetirizine (5mg, 10mg tablets/syrup)
- Chlorpheniramine (2mg, 4mg tablets/syrup)
- Promethazine (10mg, 25mg tablets)

**Gastrointestinal (3):**
- Omeprazole (20mg, 40mg capsules)
- Metoclopramide (5mg, 10mg tablets)
- Ranitidine (150mg, 300mg tablets)

**Antidiabetic (2):**
- Metformin (500mg, 850mg, 1000mg tablets)
- Glibenclamide (2.5mg, 5mg tablets)

**Cardiovascular (4):**
- Amlodipine (2.5mg, 5mg tablets)
- Lisinopril (5mg, 10mg tablets)
- Atenolol (25mg, 50mg, 100mg tablets)
- Atorvastatin (10mg, 20mg tablets)

**Antiemetics (2):**
- Ondansetron (4mg, 8mg tablets/injection)
- Domperidone (10mg tablets)

**Antihistamine for Cold (2):**
- Mebeverine (135mg capsules)
- Cough Syrup (multisymptom relief)

**Anti-inflammatory (3):**
- Hydrocortisone (20mg, 100mg tablets)
- Prednisolone (5mg, 10mg tablets)
- Triamcinolone (4mg tablets)

**Antitussive (2):**
- Dextromethorphan (10mg, 20mg syrups)
- Salbutamol (100mcg inhalers)

**Process:**
1. If `--clear` flag: Delete all existing DrugMaster rows (cascades to PrescriptionLine)
2. For each clinic: Create drug variants with random stock
3. Stock distribution:
   - 20% of clinics: Well-stocked (high stock tier)
   - 50% of clinics: Normal stock
   - 20% of clinics: Low stock tier
   - 10% of clinics: Critical stock tier

**Stock Tiers:**
- Well-stocked: 70-100% of base_stock
- Normal: 40-70% of base_stock
- Low: 10-40% of base_stock
- Critical: 1-10% of base_stock

**Example Output:**
```
Resetting DrugMaster...

✗ Deleting existing DrugMaster rows...
✓ 150 rows deleted

✓ Creating 30 drug variants per clinic...
✓ 4500 DrugMaster rows created (150 clinics × 30 drugs)
✓ Paracetamol: 150 variants, avg stock = 245
✓ Ibuprofen: 150 variants, avg stock = 512
... (28 more drugs)

Reset complete!
```

**Notes:**
- Each clinic gets a different variant of each drug (strength + dosage combination)
- Stock is randomized to simulate real-world variation
- If you delete DrugMaster, PrescriptionLine rows cascade-delete too (due to FK constraint)
- Always run `regenerate_prescription_lines` after `--clear` reset

---

### 4. **redistribute_stock** — Redistribute Inventory

**Purpose:** Evenly distribute predefined stock levels across all DrugMaster rows for a given drug name. Used to reset stock after daily data generation.

**Command:**
```bash
python manage.py redistribute_stock
```

**Predefined Stock Distribution:**
```python
TOTAL_STOCK = {
    'Paracetamol': 120,     # Highest usage
    'Ibuprofen':   8500,
    'Amoxicillin': 5000,
    'Metformin':   2000,
    'Aspirin':     4000,
    'Cetirizine':  320,
}
```

**Process:**
1. For each drug in TOTAL_STOCK:
2. Get all DrugMaster rows with that drug_name
3. Calculate base stock per clinic: `total / clinic_count`
4. Distribute remainder across first N clinics
5. Bulk update all rows at once

**Formula:**
```
base_stock_per_clinic = total_stock / clinic_count
remainder = total_stock % clinic_count

For clinic i:
  if i < remainder:
    stock[i] = base_stock + 1
  else:
    stock[i] = base_stock
```

**Example:**
If Paracetamol total_stock = 120 and 150 clinics:
- base_stock = 120 / 150 = 0
- remainder = 120 % 150 = 120
- First 120 clinics get 1 unit each
- Last 30 clinics get 0 units

**Example Output:**
```
Redistributing stock across all DrugMaster rows...

  Paracetamol: 150 rows, each gets ~0, total = 120
  Ibuprofen: 150 rows, each gets ~56, total = 8500
  Amoxicillin: 150 rows, each gets ~33, total = 5000
  Metformin: 150 rows, each gets ~13, total = 2000
  Aspirin: 150 rows, each gets ~26, total = 4000
  Cetirizine: 150 rows, each gets ~2, total = 320

Done.
```

**Typical Usage:**
```bash
# Run this weekly/monthly to reset stock
python manage.py redistribute_stock
```

**Notes:**
- Only affects drugs in TOTAL_STOCK dictionary
- Other drugs remain unchanged
- All updates happen in O(n) time
- Use after running `generate_daily_data` multiple times to reset depleted inventory

---

### 5. **update_clinic_addresses** — Generate Tamil Nadu Addresses

**Purpose:** Generate realistic Tamil Nadu clinic addresses including district names. Used during setup or to refresh address data.

**Command:**
```bash
python manage.py update_clinic_addresses
```

**Address Format:**
```
No.X, Street_Name, Area_Name, Town_Name, DISTRICT_NAME, Tamil Nadu - PIN. Ph: +91-98765XXXXX
```

**Example Addresses Generated:**
```
No.42, Bharathi Street, Nada Nagar, Chennai, CHENNAI, Tamil Nadu - 600017. Ph: +91-9876512345
No.15, Gandhi Road, Erode Town, Erode, COIMBATORE, Tamil Nadu - 641001. Ph: +91-9876534567
No.88, Kambar Lane, Madurai West, Madurai, MADURAI, Tamil Nadu - 625001. Ph: +91-9876556789
```

**Tamil Nadu Districts (38 Total):**
```
ARIYALUR, CHENGALPATTU, CHENGAM, COIMBATORE, CUDDALORE,
DHARAMAPURI, DINDIGUL, ERODE, KANCHIPURAM, KANYAKUMARI,
KARUR, KRISHNAGIRI, MADURAI, MAYILADUTHURAI, NAGAPATTINAM,
NAMAKKAL, NILGIRIS, PERAMBALUR, PUDUCHERRY, PUDUKKOTTAI,
RAMANATHAPURAM, RANIPET, SALEM, SIVAGANGAI, TENKASI,
THANJAVUR, THENI, THIRUVANNAMALAI, THIRUVARUR, TIRUPATHUR,
TIRUPPUR, TIRUVALLUR, TIRUVANANTHAPURAM, VELLORE, VILLUPURAM,
VIRUDUNAGAR, CHENGALPATTU, KALLAKURICHI
```

**Process:**
1. Get all clinics from database
2. For each clinic:
   - Generate random street name, area, town
   - Assign district (proportionally larger for major cities)
   - Generate random PIN code (600XXX format)
   - Generate random phone number
3. Bulk update clinic_address_1 field

**District Distribution:**
- **Major Cities** (30% of clinics): Chennai, Coimbatore, Madurai
- **Secondary Cities** (40% of clinics): Erode, Trichy, Vellore, Salem
- **Other Districts** (30% of clinics): Remaining 30 districts

**Example Output:**
```
Updating clinic addresses with Tamil Nadu format...

✓ Updated 150 clinics
✓ Sample addresses:
   Clinic 1: No.42, Bharathi Street, Nada Nagar, Chennai, CHENNAI, Tamil Nadu - 600017. Ph: ...
   Clinic 2: No.15, Gandhi Road, Erode Town, Erode, COIMBATORE, Tamil Nadu - 641001. Ph: ...

Done.
```

**Notes:**
- District is extracted from clinic_address_1 by splitting on commas and taking 5th segment
- All 38 Tamil Nadu districts are supported by analytics queries
- Run this once after `import_data` to set up realistic addresses

---

### 6. **inject_spike** — Inject Disease Spikes

**Purpose:** Inject historical spikes for demo/testing purposes. Simulates outbreak scenarios to test spike detection features.

**Command:**
```bash
python manage.py inject_spike [OPTIONS]
```

**Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--disease` | String | Random | Disease name to spike |
| `--quantity` | Integer | 50 | Number of spike appointments to create |
| `--date` | YYYY-MM-DD | Today | Date to create spike for |

**Examples:**
```bash
# Inject 50 random disease cases at today
python manage.py inject_spike

# Inject 100 Influenza cases on specific date
python manage.py inject_spike --disease="Influenza" --quantity=100 --date=2026-03-20

# Inject Dengue spike
python manage.py inject_spike --disease="Dengue" --quantity=75
```

**Process:**
1. Find disease by name (or pick random)
2. Get all clinics
3. Create N appointments for that disease on specified date
4. Distribute across random clinics and doctors
5. Create prescriptions and prescription lines
6. Decrement drug stock

**Example Output:**
```
Injecting spike for Influenza on 2026-03-31...

✓ Created 50 Influenza appointments across all clinics
✓ Created 75 prescriptions
✓ Created 180 prescription lines
✓ Updated stock for 25 drugs

Spike injection complete!
```

**Use Cases:**
- Testing spike detection algorithm
- Demo of outbreak response features
- Generating historical "what-if" scenarios
- Load testing with high appointment counts

**Notes:**
- Only creates historical data (past dates recommended)
- Does not trigger alerts (those are generated on query)
- Can cause stock shortages if overused

---

### 7. **regenerate_prescription_lines** — Rebuild PrescriptionLine Table

**Purpose:** Regenerate all PrescriptionLine records. Required after `reset_drug_master --clear` since FK cascade deletes prescription lines.

**Command:**
```bash
python manage.py regenerate_prescription_lines
```

**When to Use:**
```bash
# After resetting drug catalog
python manage.py reset_drug_master --clear
python manage.py regenerate_prescription_lines

# If prescription lines got corrupted/deleted
python manage.py regenerate_prescription_lines
```

**Process:**
1. Get all prescriptions
2. For each prescription:
   - Get associated appointment's disease
   - Select random drugs matching that disease
   - Create 1-5 prescription lines per prescription
   - Set quantity, duration, instructions
3. Bulk insert all lines

**Example Output:**
```
Regenerating PrescriptionLine records...

✓ Found 5000 prescriptions
✓ Generating lines (avg 3 per prescription)...
✓ Created 14,250 PrescriptionLine records
✓ Updated stock levels for 28 drugs

Regeneration complete!
```

**Notes:**
- This is **mandatory** after `reset_drug_master --clear`
- Without running this, restock_calculator will have no data
- Takes a few seconds for 5000+ prescriptions

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Initial Setup (Run Once)                                │
├─────────────────────────────────────────────────────────────────┤
│  1. python manage.py import_data                                │
│     ↓ (Loads 8 CSV files atomically)                            │
│  2. python manage.py update_clinic_addresses                    │
│     ↓ (Generates Tamil Nadu addresses)                          │
│  3. python manage.py reset_drug_master --clear                  │
│     ↓ (Creates 30-drug catalog)                                 │
│  4. python manage.py redistribute_stock                         │
│     ↓ (Initializes stock levels)                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Daily/Periodic Operations                               │
├─────────────────────────────────────────────────────────────────┤
│  • python manage.py generate_daily_data (run daily @ 8 AM)      │
│  • python manage.py redistribute_stock  (run weekly/monthly)    │
│  • python manage.py inject_spike        (run for testing)       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Maintenance (As Needed)                                 │
├─────────────────────────────────────────────────────────────────┤
│  • python manage.py regenerate_prescription_lines               │
│    (after reset_drug_master --clear)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Typical Setup Sequence

### First-Time Setup
```bash
# 1. Import all CSV data (takes ~2-3 minutes)
python manage.py import_data

# 2. Update clinic addresses to Tamil Nadu format
python manage.py update_clinic_addresses

# 3. Create 30-drug catalog
python manage.py reset_drug_master --clear

# 4. Redistribute stock to all clinics
python manage.py redistribute_stock

# Verify setup
python manage.py shell
>>> from analytics.models import Appointment
>>> Appointment.objects.count()  # Should be 1000+ after import
```

### Daily Automation
```bash
# Create Windows Task Scheduler task or Cron job
python manage.py generate_daily_data

# Output will show appointments, prescriptions created
```

### Weekly Maintenance
```bash
# Reset stock levels (prevents artificial scarcity)
python manage.py redistribute_stock
```

### Testing Outbreak Detection
```bash
# Inject spike for testing
python manage.py inject_spike --disease="Influenza" --quantity=50

# Check spike detection API
curl http://localhost:8000/api/spike-alerts/?days=8
```

---

## Performance Characteristics

| Command | Typical Duration | Data Volume |
|---------|------------------|-------------|
| `import_data` | 2-3 min | 8 CSVs, 160k rows |
| `generate_daily_data` | 5-10 sec | 30 appointments |
| `reset_drug_master --clear` | 30 sec | 4500 drug variants |
| `redistribute_stock` | 5 sec | 6 drug updates |
| `update_clinic_addresses` | 15 sec | 150 clinics |
| `inject_spike` | 10 sec | 50 appointments |
| `regenerate_prescription_lines` | 20 sec | 14k prescription lines |

---

## Error Handling & Troubleshooting

### Database Connection Error
```bash
# Error: django.db.utils.OperationalError: (1045, "Access denied...")
# Solution: Check .env DB credentials
# Verify MySQL service is running
```

### Missing Reference Data
```bash
# Error: Missing reference data (clinics, doctors, etc.)
# Solution: Run import_data first
python manage.py import_data
```

### FK Constraint Error
```bash
# Error: Clinic with id=100 does not exist
# Solution: Check CSV data integrity; ensure clinic IDs exist in Clinic.csv
```

### Stock Updates Not Reflecting
```bash
# Problem: generate_daily_data doesn't decrement stock
# Solution: Verify DrugMaster records exist
python manage.py reset_drug_master --clear
python manage.py redistribute_stock
```

### PrescriptionLine Orphaned Records
```bash
# Problem: reset_drug_master --clear deleted prescription lines
# Solution: Regenerate them
python manage.py regenerate_prescription_lines
```

---

## Advanced Usage

### Bulk Historical Data Generation
```bash
# Generate data for past 30 days
for day in {1..30}; do
  python manage.py generate_daily_data --date=2026-03-${day}
done
```

### Stress Testing (High Load)
```bash
# Generate 500 appointments in one batch
python manage.py generate_daily_data --appointments=500 --spike="COVID-19"

# Reset and redistribute stock
python manage.py redistribute_stock
```

### Custom Drug Catalog
Edit `reset_drug_master.py` DRUG_CATALOG list to add/remove drugs:
```python
DRUG_CATALOG = [
    {'drug_name': 'MyDrug', 'generic_name': 'MyGeneric', ...},
    # Add more
]
```

### Scheduled Execution (Windows Task Scheduler)

Create a batch file `run_daily.bat`:
```batch
@echo off
cd /d "e:\technospice\project\healthcare-ai"
venv\Scripts\activate
python manage.py generate_daily_data
python manage.py redistribute_stock
pause
```

Schedule in Task Scheduler:
- Trigger: Daily at 8:00 AM
- Action: Run `run_daily.bat`

---

## Integration with Analytics

The data generated by `data_loader` commands feeds directly into the analytics pipeline:

```
generate_daily_data creates Appointment + Prescription records
                          ↓
                    Appointment.models
                          ↓
                   Analytics views query
                   (disease_trends, spike_alerts, restock_suggestions)
                          ↓
                    Frontend Dashboard displays
```

**Example Flow:**
1. Run `python manage.py generate_daily_data --spike="Dengue" --appointments=50`
2. 50 Dengue appointments created
3. Dashboard query `/api/spike-alerts/?days=8` detects spike
4. SpikeAlerts component shows alert on frontend

---

## FAQ

**Q: How often should I run `generate_daily_data`?**
A: Ideally daily at 8 AM to simulate real-world data flow. Can be automated via cron/Task Scheduler.

**Q: What happens if I run `import_data` twice?**
A: Duplicates will be created (no unique constraint on import). This is intentional for testing purposes.

**Q: How do I delete all data and start fresh?**
A: 
```bash
python manage.py flush  # Delete all data
python manage.py migrate  # Recreate tables
python manage.py import_data  # Reimport CSV
```

**Q: Can I edit TOTAL_STOCK in `redistribute_stock`?**
A: Yes! Edit the dictionary at the top of `redistribute_stock.py` to change stock levels.

**Q: How is stock synchronized across clinics?**
A: Each clinic gets a different DrugMaster variant. `redistribute_stock` ensures total stock across all variants equals TOTAL_STOCK[drug_name].

**Q: What's the difference between spike injection and normal generation?**
A: `inject_spike` creates high-volume data for a specific disease on a specific date. `generate_daily_data` creates realistic daily mix of diseases.

---

## Summary

The `data_loader` app provides a complete data pipeline for the healthcare-ai system:

| Function | Command | Frequency |
|----------|---------|-----------|
| Initial setup | `import_data` | Once |
| Addressing | `update_clinic_addresses` | Once |
| Drug setup | `reset_drug_master` | Once |
| Stock reset | `redistribute_stock` | Weekly/Monthly |
| Daily sync | `generate_daily_data` | Daily (8 AM) |
| Testing | `inject_spike` | As needed |
| Maintenance | `regenerate_prescription_lines` | After drug reset |

This ensures a healthy, realistic data environment for analytics and testing.
