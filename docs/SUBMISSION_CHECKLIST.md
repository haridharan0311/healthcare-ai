# Submission Checklist

## Git Repository
- [ ] All code committed and pushed to remote
- [ ] `.venv/` in `.gitignore`
- [ ] `node_modules/` in `.gitignore`
- [ ] `requirements.txt` up to date (`pip freeze > requirements.txt`)
- [ ] `frontend/package.json` present

## Required Files
- [ ] `README.md` — ML logic, assumptions, architecture, setup instructions
- [ ] `API_DOCUMENTATION.md` — all 5 endpoints documented with params and responses
- [ ] Sample CSV output committed to repo root or `docs/` folder

## Backend (Django + DRF)
- [ ] `analytics/ml_engine.py` — moving average forecast, time decay weighting, predict_demand
- [ ] `analytics/spike_detector.py` — detect_spike(baseline_days), get_seasonal_weight
- [ ] `analytics/restock_calculator.py` — calculate_restock, apply_multi_disease_contribution
- [ ] `analytics/views.py` — all 5 API views implemented
- [ ] `analytics/serializers.py` — model + output serializers
- [ ] `analytics/urls.py` — all 5 routes registered
- [ ] `config/urls.py` — includes analytics URLs under /api/
- [ ] CORS configured for localhost:3000
- [ ] `analytics/management/commands/inject_spike.py` — demo spike command

## API Endpoints (verify all return correct data)
- [ ] GET /api/disease-trends/ — 8 diseases, sorted by trend score
- [ ] GET /api/disease-trends/timeseries/?days=7 — daily counts per disease
- [ ] GET /api/spike-alerts/ — COVID-19 spike detected
- [ ] GET /api/spike-alerts/?all=true — all 8 diseases with stats
- [ ] GET /api/restock-suggestions/ — 6 drugs, all critical status
- [ ] GET /api/export-report/ — downloads valid CSV

## ML Components (verify formulas are implemented)
- [ ] Moving average: (last_3_avg × 0.6) + (last_7_avg × 0.4)
- [ ] Time decay: recent 0.7 / older 0.3
- [ ] Spike detection: mean + 2 × std_dev
- [ ] Seasonal weight: 1.5× in-season, 1.0× off-season
- [ ] Safety buffer: 1.2× on restock calculation
- [ ] Multi-disease demand contribution

## Tests (13 passing)
- [ ] TestMovingAverage — 3 tests
- [ ] TestSpikeDetector — 6 tests (including wider baseline)
- [ ] TestRestockCalculator — 4 tests
- [ ] `python manage.py test analytics.tests.test_ml -v 2` → all OK

## Frontend (React)
- [ ] TrendChart.jsx — line chart with 13 date range options (1D–1Y)
- [ ] SpikeAlerts.jsx — red badge, SPIKE label, 8D–1Y date options
- [ ] RestockTable.jsx — status badge (critical/low/sufficient)
- [ ] ExportButton.jsx — triggers CSV download
- [ ] App.js — all 4 components assembled
- [ ] api.js — all axios calls centralised

## Data Quality
- [ ] Generic names corrected (Acetaminophen, Ibuprofen, etc.)
- [ ] current_stock set to realistic values per drug
- [ ] Disease names normalised (trailing numbers stripped in logic)
- [ ] Spike injected via management command

## Final Checks
- [ ] Django server starts without errors: `python manage.py runserver`
- [ ] React app starts without errors: `npm start`
- [ ] All 5 API endpoints return 200 in browser
- [ ] Dashboard loads at localhost:3000
- [ ] CSV download works from browser and from Export button
- [ ] Git log shows meaningful commit messages
