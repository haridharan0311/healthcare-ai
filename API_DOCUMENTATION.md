# API Documentation

Base URL: http://localhost:8000/api

All endpoints return application/json unless noted.
No authentication required in development mode.

---

## Analytics APIs (5 endpoints)

---

### 1. Disease Trends

GET /api/disease-trends/

Returns all active diseases ranked by weighted trend score with seasonal adjustment applied.

Query Parameters:
  days    integer    30    Number of days to analyse

Response:
```json
[
  {
    "disease_name": "COVID-19",
    "season": "Summer",
    "total_cases": 294,
    "trend_score": 230.1,
    "seasonal_weight": 1.5
  },
  {
    "disease_name": "Flu",
    "season": "Summer",
    "total_cases": 295,
    "trend_score": 222.75,
    "seasonal_weight": 1.5
  }
]
```

Field Notes:
  disease_name      canonical type name (trailing numbers stripped from synthetic data)
  trend_score       weighted_trend_score x seasonal_weight — higher means more urgent
  seasonal_weight   1.5x if disease is in its active season, 1.0x otherwise
  total_cases       sum of recent + older cases in the selected window

Logic:
  1. Split window: last 7 days = recent, remainder = older
  2. weighted_trend = (recent x 0.7) + (older x 0.3)
  3. Multiply by seasonal weight
  4. Sort descending by trend_score

---

### 2. Time-Series

GET /api/disease-trends/timeseries/

Returns daily case counts per disease for graph plotting.

Query Parameters:
  days      integer    7    Number of days to include
  disease   string     —    Filter to single disease (e.g. COVID-19)

Response:
```json
[
  {
    "date": "2026-03-23",
    "disease_name": "Flu",
    "case_count": 49
  },
  {
    "date": "2026-03-23",
    "disease_name": "Diabetes",
    "case_count": 43
  }
]
```

Notes:
  Dates with no cases are omitted (not zero-filled).
  Results sorted by date ascending.
  Disease names normalised — trailing numbers stripped from synthetic data.
  Date range options supported: 3D, 4D, 5D, 1W, 2W, 3W, 1M, 2M, 3M, 6M, 1Y

---

### 3. Spike Alerts

GET /api/spike-alerts/

Detects diseases with abnormal case counts using statistical baseline analysis.

Query Parameters:
  days    integer    8       Baseline window in days (minimum enforced at 8)
  all     boolean    false   If true, returns all diseases including non-spikes

Response:
```json
[
  {
    "disease_name": "Flu",
    "period_count": 196,
    "today_count": 49,
    "mean_last_7_days": 15.71,
    "std_dev": 9.43,
    "threshold": 34.57,
    "is_spike": true
  },
  {
    "disease_name": "Diabetes",
    "period_count": 168,
    "today_count": 43,
    "mean_last_7_days": 16.86,
    "std_dev": 11.33,
    "threshold": 39.53,
    "is_spike": true
  }
]
```

Spike Detection Formula:
  threshold = mean(baseline_days) + 2 x std_dev(baseline_days)
  is_spike  = today_count > threshold

Field Notes:
  period_count      total cases across the entire selected window
  today_count       cases on the latest date in DB
  mean_last_7_days  mean of the baseline window (field name kept for compatibility)
  threshold         the computed spike boundary

Baseline Window Behaviour:
  8D     7-day baseline    sensitive to short-term spikes
  2W     13-day baseline   moderate sensitivity
  1M     29-day baseline   smoothed by monthly pattern
  1Y     364-day baseline  only extreme outliers flagged

---

### 4. Restock Suggestions (System-wide)

GET /api/restock-suggestions/

Calculates predicted medicine demand and suggests restock quantities.
System-wide view — all clinics combined, grouped by drug name.

Query Parameters:
  days    integer    30    Analysis window in days

Response:
```json
[
  {
    "drug_name": "Cetirizine",
    "generic_name": "Cetirizine hydrochloride",
    "current_stock": 320,
    "predicted_demand": 5753.0,
    "suggested_restock": 5433,
    "status": "critical",
    "contributing_diseases": ["Allergy", "Asthma", "COVID-19", "Flu", "Diabetes"]
  },
  {
    "drug_name": "Ibuprofen",
    "generic_name": "Ibuprofen",
    "current_stock": 8500,
    "predicted_demand": 5652.8,
    "suggested_restock": 0,
    "status": "sufficient",
    "contributing_diseases": ["Flu", "Arthritis", "Migraine"]
  }
]
```

Status Values:
  critical     shortage > 50% of expected demand
  low          shortage <= 50%
  sufficient   no restock needed

Calculation:
  combined_demand   = sum(disease_demand x seasonal_weight) for all contributing diseases
  expected_demand   = combined_demand x avg_qty_per_prescription x 1.2
  suggested_restock = max(0, expected_demand - current_stock)

---

### 5. District Restock

GET /api/district-restock/

When called without district: returns list of all 38 Tamil Nadu districts.
When called with district: returns detailed drug restock for that district.
Each result row represents one unique drug + strength + dosage combination.

Query Parameters:
  district    string     —     Tamil Nadu district name (e.g. Chennai, Coimbatore)
  days        integer    30    Analysis window in days

Response without district (district list):
```json
{
  "districts": [
    "Ariyalur", "Chennai", "Chengalpet", "Coimbatore",
    "Cuddalore", "Dharmapuri", "Dindigul", "Erode", ...
  ],
  "total": 38
}
```

Response with district:
```json
{
  "district": "Coimbatore",
  "clinic_count": 987,
  "period": "2026-02-21 to 2026-03-23",
  "summary": {
    "total_drugs": 94,
    "critical": 18,
    "low": 35,
    "sufficient": 41
  },
  "results": [
    {
      "drug_name": "Paracetamol",
      "generic_name": "Acetaminophen",
      "drug_strength": "500mg",
      "dosage_type": "Tablet",
      "district": "Coimbatore",
      "clinic_count": 247,
      "current_stock": 1840,
      "predicted_demand": 312.4,
      "suggested_restock": 0,
      "status": "sufficient",
      "contributing_diseases": ["Flu", "COVID-19", "Diabetes", "Arthritis"]
    },
    {
      "drug_name": "Cetirizine",
      "generic_name": "Cetirizine hydrochloride",
      "drug_strength": "10mg",
      "dosage_type": "Tablet",
      "district": "Coimbatore",
      "clinic_count": 198,
      "current_stock": 24,
      "predicted_demand": 250.8,
      "suggested_restock": 226,
      "status": "critical",
      "contributing_diseases": ["Allergy", "Asthma", "COVID-19"]
    }
  ]
}
```

District Demand Calculation:
  district_demand = system_demand x (district_clinic_count / total_clinics)

Results sorted: critical first, then low, then sufficient, then by drug name + strength.

---

## Export APIs (3 endpoints)

---

### 6. Export — Disease Trends CSV

GET /api/export/disease-trends/

Downloads disease trend report as CSV. One row per disease type.

Query Parameters:
  days    integer    30    Analysis window in days

Response:
  Content-Type: text/csv
  Filename: disease_trends_YYYY-MM-DD.csv

Columns:
  Disease, Season, Category, Severity, Total Cases, Recent Cases (7d),
  Older Cases, Trend Score, Seasonal Weight, Status, Period Start, Period End

Sample row:
  COVID-19, Summer, Chronic, 1, 294, 163, 131, 230.1, 1.5, High, 2026-02-21, 2026-03-23

---

### 7. Export — Spike Alerts CSV

GET /api/export/spike-alerts/

Downloads spike alert report as CSV. Spike rows appear first, then sorted by today_count.

Query Parameters:
  days    integer    8    Baseline window in days (minimum 8)

Response:
  Content-Type: text/csv
  Filename: spike_alerts_YYYY-MM-DD.csv

Columns:
  Disease, Season, Today Count, Period Count, Mean (baseline),
  Std Dev, Threshold, Is Spike, Severity, Baseline Days, As Of Date

Sample row:
  Flu, Summer, 49, 196, 15.71, 9.43, 34.57, YES, 4, 7, 2026-03-23

---

### 8. Export — Restock Suggestions CSV (Detailed)

GET /api/export/restock/

Downloads detailed restock report. One row per DrugMaster record.
Covers every clinic, every drug strength, every dosage type across Tamil Nadu.

Query Parameters:
  days    integer    30    Analysis window in days

Response:
  Content-Type: text/csv
  Filename: restock_suggestions_YYYY-MM-DD.csv

Columns:
  Drug Name, Generic Name, Drug Strength, Dosage Type,
  Clinic Name, District,
  Current Stock, Predicted Demand,
  Suggested Restock, Status,
  Contributing Diseases, Period

Sample rows:
  Cetirizine, Cetirizine hydrochloride, 10mg, Tablet, Henry and Sons Clinic, Chennai,
    0, 3875.85, 3875, critical, "Allergy, COVID-19, Flu", 2026-02-21 to 2026-03-23

  Ibuprofen, Ibuprofen, 400mg, Tablet, Shelton-Bell Clinic, Coimbatore,
    450, 312.4, 0, sufficient, "Flu, Arthritis", 2026-02-21 to 2026-03-23

Notes:
  Demand is prorated per clinic: system_demand / total_clinics
  Sorted: critical first, then by drug name, then by clinic name
  Covers all 30 drug types across all 20,000 clinics (~100,000 rows)

---

### 9. Legacy Combined Export

GET /api/export-report/

Downloads a single CSV with all three sections combined.
Kept for backward compatibility. Prefer the 3 separate endpoints above.

Query Parameters:
  days    integer    30    Analysis window in days

Response:
  Content-Type: text/csv
  Filename: health_report_YYYY-MM-DD.csv

---

## CRUD APIs (8 model endpoints)

All CRUD endpoints follow standard REST conventions.
Base prefix: /api/crud/

Operations supported for every model:
  GET     /api/crud/{model}/          List all — paginated, searchable
  POST    /api/crud/{model}/          Create new record
  GET     /api/crud/{model}/{id}/     Retrieve single record
  PUT     /api/crud/{model}/{id}/     Full update
  PATCH   /api/crud/{model}/{id}/     Partial update
  DELETE  /api/crud/{model}/{id}/     Delete record

Available model endpoints:
  /api/crud/clinics/
  /api/crud/doctors/
  /api/crud/patients/
  /api/crud/diseases/
  /api/crud/appointments/
  /api/crud/drugs/
  /api/crud/prescriptions/
  /api/crud/prescription-lines/

Pagination query params:
  ?page=1           Page number (default 1)
  ?page_size=20     Records per page (default 20, max 100)

Search:
  ?search=Chennai   Filters by searchable fields defined per model

---

### FK Dropdowns Endpoint

GET /api/crud/dropdowns/

Returns all FK option lists in a single call.
Used by the admin panel form to populate searchable dropdown selectors.

Response:
```json
{
  "clinics":       [{"value": 1, "label": "Henry and Sons Clinic"}, ...],
  "doctors":       [{"value": 1, "label": "Brianna Grimes"}, ...],
  "patients":      [{"value": 1, "label": "Manuel Walker"}, ...],
  "diseases":      [{"value": 1, "label": "Allergy 6"}, ...],
  "appointments":  [{"value": 1, "label": "OP115736 - 2025-05-26"}, ...],
  "drugs":         [{"value": 1, "label": "Paracetamol (Acetaminophen)"}, ...],
  "prescriptions": [{"value": 1, "label": "Prescription 1 - 2025-11-03"}, ...]
}
```

---

## Error Responses

  200    Success
  400    Invalid query parameter
  404    Record not found
  500    Server error — check Django runserver logs

---

## Sample curl Commands

```bash
# ── Analytics APIs ────────────────────────────────────────────────────

# Disease trends — last 30 days
curl "http://localhost:8000/api/disease-trends/?days=30"

# Time series — last 7 days, Flu only
curl "http://localhost:8000/api/disease-trends/timeseries/?days=7&disease=Flu"

# Spike alerts — 8-day baseline, spikes only
curl "http://localhost:8000/api/spike-alerts/"

# Spike alerts — 30-day baseline, all diseases
curl "http://localhost:8000/api/spike-alerts/?all=true&days=30"

# System-wide restock
curl "http://localhost:8000/api/restock-suggestions/"

# ── District restock ──────────────────────────────────────────────────

# Get list of all 38 districts
curl "http://localhost:8000/api/district-restock/"

# Coimbatore district restock — last 30 days
curl "http://localhost:8000/api/district-restock/?district=Coimbatore&days=30"

# Chennai district restock — last 90 days
curl "http://localhost:8000/api/district-restock/?district=Chennai&days=90"

# ── CSV exports ───────────────────────────────────────────────────────

# Disease trends CSV
curl -OJ "http://localhost:8000/api/export/disease-trends/"

# Spike alerts CSV
curl -OJ "http://localhost:8000/api/export/spike-alerts/"

# Detailed restock CSV (all clinics, all drugs)
curl -OJ "http://localhost:8000/api/export/restock/"

# ── CRUD APIs ─────────────────────────────────────────────────────────

# List clinics — page 2
curl "http://localhost:8000/api/crud/clinics/?page=2"

# Search doctors
curl "http://localhost:8000/api/crud/doctors/?search=Kumar"

# Get a single disease
curl "http://localhost:8000/api/crud/diseases/1/"

# Create a new disease
curl -X POST "http://localhost:8000/api/crud/diseases/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Dengue","season":"Monsoon","severity":3,"is_active":true}'

# Update a clinic
curl -X PATCH "http://localhost:8000/api/crud/clinics/1/" \
  -H "Content-Type: application/json" \
  -d '{"clinic_name":"Updated Clinic Name"}'

# Delete a record
curl -X DELETE "http://localhost:8000/api/crud/prescriptions/5/"

# FK dropdowns for admin form
curl "http://localhost:8000/api/crud/dropdowns/"
```
