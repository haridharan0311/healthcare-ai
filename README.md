# AI-Powered Disease Trend Analysis & Medicine Restock System

A healthcare analytics platform that learns from historical clinical data, detects disease trends and anomalies, predicts future medicine demand, and suggests intelligent restocking decisions through an interactive dashboard.

---

## Project Architecture

```
healthcare_ai/
├── config/                  # Django project settings
├── core/                    # Core models: Clinic, Doctor, Patient, Disease, Appointment
├── inventory/               # Inventory models: DrugMaster, Prescription, PrescriptionLine
├── analytics/               # Intelligence layer
│   ├── views.py             # 5 API endpoints
│   ├── serializers.py       # DRF serializers
│   ├── ml_engine.py         # Moving average forecast
│   ├── spike_detector.py    # Anomaly detection
│   ├── restock_calculator.py# Demand prediction + restock logic
│   ├── urls.py              # API routing
│   ├── management/
│   │   └── commands/
│   │       └── inject_spike.py  # Demo spike injection
│   └── tests/
│       └── test_ml.py       # 13 unit tests
└── frontend/                # React dashboard
    └── src/
        ├── App.js
        ├── api.js
        └── components/
            ├── TrendChart.jsx
            ├── SpikeAlerts.jsx
            ├── RestockTable.jsx
            └── ExportButton.jsx
```

---

## ML Logic Explanation

### 1. Moving Average Forecast

Forecasts next-day case count by blending two windows:

```
Forecast = (avg_last_3_days × 0.6) + (avg_last_7_days × 0.4)
```

Recent data (last 3 days) gets 60% weight because disease trends shift quickly. The 7-day average provides stability against single-day noise.

**File:** `analytics/ml_engine.py → moving_average_forecast()`

---

### 2. Time Decay Weighting

Data from the last 7 days is treated as "recent" and weighted at 0.7. Data older than 7 days is weighted at 0.3:

```
weighted_trend = (recent_count × 0.7) + (older_count × 0.3)
```

This ensures the trend score reflects current conditions more than historical baseline.

**File:** `analytics/ml_engine.py → weighted_trend_score()`

---

### 3. Seasonal Adjustment

Each disease has a season (`Summer`, `Monsoon`, `Winter`, `All`). During its active season, the trend score is multiplied by 1.5×:

```
Season      Active Months       Multiplier
Summer      March – June        1.5×
Monsoon     July – October      1.5×
Winter      November – February 1.5×
Off-season  (any other month)   1.0×
```

**File:** `analytics/spike_detector.py → get_seasonal_weight()`

---

### 4. Spike Detection

Uses a statistical baseline to flag abnormal case counts:

```
Spike if: today_count > (mean_last_N_days + 2 × std_dev)
```

The baseline window N is configurable via the `?days=` query param (minimum 8). A wider window (e.g. 1Y) raises the threshold; a tight window (8D) is more sensitive to short-term spikes.

**File:** `analytics/spike_detector.py → detect_spike(baseline_days)`

---

### 5. Demand Prediction

```
predicted_cases = weighted_trend_score + moving_average_forecast
```

**File:** `analytics/ml_engine.py → predict_demand()`

---

### 6. Restock Calculation

```
expected_demand = predicted_cases × avg_quantity_per_prescription × 1.2 (safety buffer)
suggested_restock = max(0, expected_demand − current_stock)
```

When multiple diseases contribute to demand for one drug, their demands are combined with seasonal weights:

```
combined_demand = Σ (disease_demand × seasonal_weight)
```

Status thresholds:
- `critical` — shortage > 50% of expected demand
- `low`      — shortage ≤ 50%
- `sufficient` — no restock needed

**File:** `analytics/restock_calculator.py`

---

## Assumptions

1. **Disease grouping** — Synthetic data created thousands of unique disease rows with numeric suffixes (e.g. `"Dengue 1842"`). These are grouped by disease type using a regex strip of trailing numbers. All analysis operates on ~8–10 canonical disease types.

2. **Inventory pooling** — `current_stock` is summed across all `DrugMaster` rows sharing the same `drug_name`. In production, restock would be evaluated per clinic. This implementation treats the dataset as a single inventory pool.

3. **Date-relative queries** — All date windows are relative to the latest `appointment_datetime` in the database, not the server's calendar date. This ensures synthetic historical data works correctly without any date shifting.

4. **Spike injection** — A single COVID-19 spike (32 cases) was injected via `python manage.py inject_spike` to demonstrate the spike detection feature, since synthetic data distributes cases uniformly across time.

5. **Generic names** — Synthetic data randomised `generic_name` independently of `drug_name`. All generic names were corrected via a bulk update in the Django shell before submission.

---

## Setup Instructions

### Backend

```bash
# 1. Clone the repository
git clone healthcare-ai
cd healthcare_ai

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Import synthetic data (if starting fresh)
python manage.py import_csv   # or your custom import command

# 6. Inject demo spike
python manage.py inject_spike

# 7. Start server
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:3000`

---

## Running Tests

```bash
python manage.py test analytics.tests.test_ml -v 2
```

**13 tests covering:**
- Moving average forecast (normal, empty, single value)
- Spike detection (spike, no spike, insufficient data, wider baseline)
- Seasonal weights (in-season, out-of-season)
- Restock calculation (restock needed, no restock, multi-disease contribution)

---

## Tech Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Backend  | Django 6.x, Django REST Framework |
| ML       | Pure Python (statistics module)   |
| Frontend | React, Recharts, Axios            |
| Database | SQLite (dev) / PostgreSQL (prod)  |
| Export   | Python csv module                 |
