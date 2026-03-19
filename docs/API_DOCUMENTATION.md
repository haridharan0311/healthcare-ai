# API Documentation

Base URL: `http://localhost:8000/api`

All endpoints return `application/json` unless noted. No authentication required (development mode).

---

## 1. Disease Trends

**`GET /api/disease-trends/`**

Returns all active diseases ranked by weighted trend score, with seasonal adjustment applied.

### Query Parameters

| Parameter | Type    | Default | Description                        |
|-----------|---------|---------|------------------------------------|
| `days`    | integer | 30      | Number of days to analyse          |

### Response

```json
[
  {
    "disease_name":     "Diabetes",
    "season":           "Summer",
    "total_cases":      124,
    "trend_score":      72.6,
    "seasonal_weight":  1.5
  }
]
```

### Field Notes

| Field            | Description                                                  |
|------------------|--------------------------------------------------------------|
| `trend_score`    | `weighted_trend_score × seasonal_weight`. Higher = more urgent |
| `seasonal_weight`| 1.5× if disease is in its active season, 1.0× otherwise     |
| `total_cases`    | Sum of recent + older cases within the selected date window  |

### Logic

1. Split the date window into two halves: last 7 days (recent) and the remainder (older)
2. Apply `weighted_trend = (recent × 0.7) + (older × 0.3)`
3. Multiply by seasonal weight
4. Sort descending by trend score

---

## 2. Time-Series

**`GET /api/disease-trends/timeseries/`**

Returns daily case counts per disease for graph plotting.

### Query Parameters

| Parameter | Type    | Default | Description                                |
|-----------|---------|---------|--------------------------------------------|
| `days`    | integer | 7       | Number of days to include                  |
| `disease` | string  | —       | Filter to a single disease (e.g. `Dengue`) |

### Response

```json
[
  {
    "date":         "2026-03-18",
    "disease_name": "COVID-19",
    "case_count":   32
  }
]
```

### Notes
- Dates with no cases are omitted (not filled with zeros)
- Results are sorted by date ascending
- Disease names are normalised (trailing numbers stripped from synthetic data)

---

## 3. Spike Alerts

**`GET /api/spike-alerts/`**

Detects diseases with abnormal case counts using statistical baseline analysis.

### Query Parameters

| Parameter | Type    | Default | Description                                        |
|-----------|---------|---------|----------------------------------------------------|
| `days`    | integer | 8       | Baseline window in days (minimum enforced at 8)    |
| `all`     | boolean | false   | If `true`, returns all diseases including non-spikes |

### Response

```json
[
  {
    "disease_name":      "COVID-19",
    "today_count":       32,
    "mean_last_7_days":  3.71,
    "std_dev":           2.06,
    "threshold":         7.83,
    "is_spike":          true
  }
]
```

### Spike Detection Formula

```
threshold = mean(baseline_days) + 2 × std_dev(baseline_days)
is_spike  = today_count > threshold
```

### Baseline Window Effect

| Option | Baseline | Behaviour                              |
|--------|----------|----------------------------------------|
| 8D     | 7 days   | Sensitive — detects short-term spikes  |
| 1M     | 29 days  | Moderate — smoothed by monthly pattern |
| 1Y     | 364 days | Stable — only extreme outliers flagged |

---

## 4. Restock Suggestions

**`GET /api/restock-suggestions/`**

Calculates predicted medicine demand and suggests restock quantities per drug.

### Query Parameters

| Parameter | Type    | Default | Description               |
|-----------|---------|---------|---------------------------|
| `days`    | integer | 30      | Analysis window in days   |

### Response

```json
[
  {
    "drug_name":             "Cetirizine",
    "generic_name":          "Cetirizine hydrochloride",
    "current_stock":         150,
    "predicted_demand":      3057.9,
    "suggested_restock":     2907,
    "contributing_diseases": ["COVID-19", "Flu", "Allergy", "Asthma"],
    "status":                "critical"
  }
]
```

### Field Notes

| Field                  | Description                                               |
|------------------------|-----------------------------------------------------------|
| `predicted_demand`     | Combined demand across all contributing diseases × safety buffer (1.2×) |
| `suggested_restock`    | `max(0, predicted_demand − current_stock)`               |
| `status`               | `critical` (shortage > 50%), `low` (≤ 50%), `sufficient` |
| `contributing_diseases`| All disease types that drove prescriptions for this drug |

### Calculation Pipeline

```
1. For each disease type:
   daily_counts → moving_average_forecast()
   recent/older counts → weighted_trend_score()
   demand = predict_demand(trend, forecast)
   demand × seasonal_weight

2. For each drug:
   combined_demand = Σ(disease_demand × seasonal_weight)
   expected = combined_demand × avg_qty_per_prescription × 1.2
   suggested_restock = max(0, expected − current_stock)
```

---

## 5. CSV Export

**`GET /api/export-report/`**

Downloads a CSV report containing all three sections.

### Query Parameters

| Parameter | Type    | Default | Description             |
|-----------|---------|---------|-------------------------|
| `days`    | integer | 30      | Analysis window in days |

### Response

- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="health_report_YYYY-MM-DD.csv"`

### CSV Structure

```
[blank line]
DISEASE TREND REPORT, Period: YYYY-MM-DD to YYYY-MM-DD
Disease, Season, Total Cases, Trend Score, Seasonal Weight, Status
...

[blank line]
SPIKE ALERTS, As of: YYYY-MM-DD
Disease, Today Count, Mean (7d), Std Dev, Threshold, Spike?
...

[blank line]
RESTOCK SUGGESTIONS
Drug, Generic Name, Current Stock, Predicted Demand, Suggested Restock, Status, Contributing Diseases
...
```

---

## Error Responses

All endpoints return standard HTTP status codes:

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success                              |
| 400  | Invalid query parameter              |
| 500  | Server error (check Django logs)     |

---

## Sample curl Commands

```bash
# Disease trends — last 30 days
curl http://localhost:8000/api/disease-trends/?days=30

# Time series — last 7 days, COVID-19 only
curl "http://localhost:8000/api/disease-trends/timeseries/?days=7&disease=COVID-19"

# All spike alerts with 30-day baseline
curl "http://localhost:8000/api/spike-alerts/?all=true&days=30"

# Restock suggestions
curl http://localhost:8000/api/restock-suggestions/

# Download CSV report
curl -O http://localhost:8000/api/export-report/
```
