# AI-Powered Disease Trend Analysis & Medicine Restock System

A healthcare analytics platform built for Tamil Nadu clinical data.
Detects disease trends, identifies anomalies, predicts medicine demand, and
suggests intelligent restocking decisions through an interactive dashboard
with district-level filtering across all 38 Tamil Nadu districts.

---

## Project Structure

```
healthcare_ai/
├── config/                              # Django project settings and URLs
├── core/                                # Core models
│   └── models.py                        # Clinic, Doctor, Patient
├── analytics/                           # Intelligence layer
│   ├── models.py                        # Disease, Appointment
│   ├── views.py                         # 9 API endpoints
│   ├── serializers.py                   # DRF output serializers
│   ├── crud_views.py                    # CRUD ViewSets + dropdown endpoint
│   ├── crud_serializers.py              # CRUD serializers with FK names
│   ├── ml_engine.py                     # Moving average + trend scoring
│   ├── restock_calculator.py            # Demand prediction + restock logic
│   ├── spike_detector.py                # Statistical anomaly detection
│   ├── urls.py                          # All API routing
│   └── tests/
│       └── test_ml.py                   # 13 unit tests
├── inventory/                           # Inventory models
│   └── models.py                        # DrugMaster, Prescription, PrescriptionLine
├── data_loader/
│   └── management/commands/
│       ├── import_data.py               # CSV to DB import
│       ├── inject_spike.py              # Demo spike injection
│       ├── generate_daily_data.py       # Daily automation command
│       ├── redistribute_stock.py        # Stock redistribution utility
│       ├── reset_drug_master.py         # 30-drug catalog setup
│       ├── update_clinic_addresses.py   # Tamil Nadu address generator
│       └── regenerate_prescription_lines.py  # Rebuild lines after drug reset
├── data/                                # Source CSV files (8 models, 20k rows each)
│   ├── appointment.csv
│   ├── clinic.csv
│   ├── disease.csv
│   ├── doctor.csv
│   ├── drugmaster.csv
│   ├── patient.csv
│   ├── prescription.csv
│   └── prescriptionline.csv
├── sample_outputs/                      # Dashboard screenshots (7 images)
├── frontend/
│   └── src/
│       ├── App.js                       # Main app with routing
│       ├── api.js                       # All axios calls centralised
│       ├── admin/
│       │   ├── AdminLayout.jsx          # Dark sidebar navigation
│       │   ├── ModelList.jsx            # Paginated table with search
│       │   └── ModelForm.jsx            # Create/edit with FK dropdowns
│       └── components/
│           ├── TrendChart.jsx           # Line chart with 3D to 1Y range
│           ├── SpikeAlerts.jsx          # Spike panel with 8D to 1Y range
│           ├── DistrictRestock.jsx      # District-level restock table
│           └── ExportButton.jsx         # 3 separate CSV download buttons
├── Generate_data_commands.md            # Daily data generation cheatsheet
├── .env                                 # Database credentials (not committed)
├── requirements.txt
└── manage.py
```

---

## ML Logic Explanation

### 1. Moving Average Forecast

```
Forecast = (avg_last_3_days x 0.6) + (avg_last_7_days x 0.4)
```

Recent data (last 3 days) gets 60% weight because disease trends shift quickly.
The 7-day average provides stability against single-day noise.

File: analytics/ml_engine.py → moving_average_forecast()

---

### 2. Time Decay Weighting

```
weighted_trend = (recent_count x 0.7) + (older_count x 0.3)
```

Data from the last 7 days is weighted at 0.7. Data older than 7 days is weighted at 0.3.
Ensures trend score reflects current conditions more than historical baseline.

File: analytics/ml_engine.py → weighted_trend_score()

---

### 3. Seasonal Adjustment

Each disease has a season. During its active season, the trend score is multiplied by 1.5x.

```
Season      Active Months         Multiplier
Summer      March to June         1.5x
Monsoon     July to October       1.5x
Winter      November to February  1.5x
Off-season  any other month       1.0x
```

File: analytics/spike_detector.py → get_seasonal_weight()

---

### 4. Spike Detection

Statistical baseline used to flag abnormal case counts.
Baseline window N is configurable via ?days= param (minimum 8 days).

```
threshold = mean(last_N_days) + 2 x std_dev(last_N_days)
is_spike  = today_count > threshold
```

A wider window (1Y) raises the threshold — only extreme outliers flagged.
A tight window (8D) is sensitive to short-term spikes.

File: analytics/spike_detector.py → detect_spike(baseline_days)

---

### 5. Demand Prediction

```
predicted_cases = weighted_trend_score + moving_average_forecast
```

File: analytics/ml_engine.py → predict_demand()

---

### 6. Restock Calculation

```
expected_demand   = predicted_cases x avg_qty_per_prescription x 1.2
suggested_restock = max(0, expected_demand - current_stock)
```

For district-level analysis, system demand is prorated by clinic proportion:

```
district_demand = system_demand x (district_clinic_count / total_clinics)
```

Multi-disease contribution:

```
combined_demand = sum(disease_demand x seasonal_weight)
```

Status thresholds:
  critical    shortage > 50% of expected demand
  low         shortage <= 50%
  sufficient  no restock needed

File: analytics/restock_calculator.py

---

## Assumptions

1. Disease grouping
   Synthetic data has numeric suffixes like "Dengue 1842".
   Grouped by type using regex strip. All analysis uses ~8 canonical disease types.

2. District-level inventory
   Dashboard summary shows system-wide totals.
   District restock shows district-prorated demand vs district-total stock per
   unique drug + strength + dosage combination.

3. Date-relative queries
   All windows use the latest appointment_datetime in DB, not server calendar date.
   Ensures synthetic historical data works correctly without date shifting.

4. Tamil Nadu address format
   No.X, Street, Area, Town, District, Tamil Nadu - PIN. Ph: number
   District is always extracted from the 5th comma-separated segment.
   All 38 districts covered. Larger cities get proportionally more clinics.

5. Drug catalog
   30 drugs across 8 clinical categories. Each clinic gets 5 random drug variants.
   Stock tiers: 20% well-stocked, 50% normal, 20% low, 10% critical.

6. Generic names
   All generic names corrected via bulk update.
   GENERIC_MAP in views.py is the authoritative reference.

7. Prescription line regeneration
   Running reset_drug_master --clear deletes DrugMaster rows.
   Since PrescriptionLine has on_delete=CASCADE to DrugMaster,
   prescription lines are also deleted. Run regenerate_prescription_lines
   after any DrugMaster reset to rebuild them.

---

## Setup Instructions

### Prerequisites

- Python 3.13+
- Node.js 18+
- MySQL (production) or SQLite (development)

### Backend

```bash
# 1. Clone the repository
git clone https://github.com/haridharan0311/healthcare-ai.git
cd healthcare_ai

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure database
# Copy .env.example to .env and set your DB credentials
# For SQLite development, no changes needed

# 5. Run migrations
python manage.py migrate

# 6. Import synthetic data (8 CSVs from data/ folder)
python manage.py import_data

# 7. Update clinic addresses to Tamil Nadu format
python manage.py update_clinic_addresses

# 8. Set up 30-drug catalog with realistic stock
python manage.py reset_drug_master --clear --drugs-per-clinic 5

# 9. Redistribute stock evenly
python manage.py redistribute_stock

# 10. Rebuild prescription lines (after drug reset)
python manage.py regenerate_prescription_lines

# 11. Inject demo spikes for dashboard activity
python manage.py inject_spike

# 12. Start server
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:3000

Admin panel at http://localhost:3000/admin-panel

---

## Running Tests

```bash
python manage.py test analytics.tests.test_ml -v 2
```

13 tests covering:
  TestMovingAverage (3)      normal, empty input, single value
  TestSpikeDetector (6)      spike detected, no spike, insufficient data,
                             wider baseline, in-season weight, out-of-season weight
  TestRestockCalculator (4)  restock needed, no restock, multi-disease contribution,
                             status thresholds

---

## Daily Data Automation

```bash
# Generate today's data (30 appointments by default)
python manage.py generate_daily_data

# With a spike and custom appointment count
python manage.py generate_daily_data --date 2026-03-25 --appointments 40 --spike COVID-19
```

Set up Windows Task Scheduler with run_daily.bat at 8am for fully automated daily data.
See Generate_data_commands.md and docs/DATA_LOADER.md for the full command reference.

---

## Tech Stack

| Layer        | Technology                              |
|--------------|-----------------------------------------|
| Backend      | Django 6.x, Django REST Framework      |
| ML Engine    | Pure Python (statistics module)         |
| Frontend     | React, Recharts, React Router, Axios   |
| Database     | MySQL (production), SQLite (dev)        |
| Export       | Python csv module                       |
| Geography    | Tamil Nadu 38-district address system  |
| Admin Panel  | Custom React CRUD with FK dropdowns    |
