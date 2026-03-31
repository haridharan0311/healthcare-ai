# Healthcare AI Platform

A production-ready healthcare analytics and medicine inventory management system for Tamil Nadu clinical networks.

## Overview

Healthcare AI is an intelligent platform that combines real-time disease surveillance, AI-driven medicine demand forecasting, and automated inventory recommendations. It helps public health administrators and pharmacists across Tamil Nadu districts make data-driven decisions about resource allocation and outbreak response.

### Key Capabilities

- **Disease Trend Analysis** — Track case counts across disease types with seasonal weighting
- **Outbreak Detection** — Statistical anomaly detection (Mean + 2σ threshold) for spike alerts
- **Demand Forecasting** — ML-based predictions using weighted moving averages
- **Smart Restocking** — Multi-factor algorithm suggesting optimal medicine quantities
- **District-Level Analytics** — All 38 Tamil Nadu districts with drill-down filtering
- **Interactive Dashboard** — Real-time visualizations with 1-week to 1-year time ranges
- **CRUD Admin Panel** — Full data management for 8 core entities
- **CSV Export** — Download trend, spike, and restock data

---

## Tech Stack

| Component | Technologies |
|-----------|---------------|
| **Backend** | Django 6.0.3, Django REST Framework |
| **Frontend** | React 18+, Recharts, Axios |
| **Database** | MySQL 8+ (SQLite for development) |
| **Data Processing** | NumPy, Pandas |
| **CORS** | django-cors-headers |
| **Environment** | Python 3.8+, Node.js 16+ |

---

## Architecture

### Backend Structure

```
config/              Project settings & routing
├── core/            Domain models (Clinic, Doctor, Patient)
├── analytics/       Intelligence layer (disease trends, ML, spike detection)
├── inventory/       Stock & pharmacy models (DrugMaster, Prescription)
└── data_loader/     Data import & synchronization
```

### Database Schema

**Core Models**
- **Clinic** — Healthcare facility with address and metadata
- **Doctor** — Licensed practitioners assigned to clinics
- **Patient** — Individuals receiving care

**Analytics Models**
- **Disease** — Clinical conditions with severity and seasonal attributes
- **Appointment** — Clinical visits linking patient, doctor, disease, and clinic

**Inventory Models**
- **DrugMaster** — Medicine catalog per clinic with current stock levels
- **Prescription** — Medicine orders for patients
- **PrescriptionLine** — Individual drug items within prescriptions

### Frontend Structure

```
frontend/src/
├── pages/
│   ├── Dashboard.jsx       Main analytics hub
│   ├── ReportsPage.jsx     Weekly/monthly reports
│   ├── AdminLayout.jsx     CRUD management interface
│   ├── ModelList.jsx       Entity listing (paginated)
│   └── ModelForm.jsx       Create/edit forms
├── components/
│   ├── TrendChart.jsx      Time-series visualization
│   ├── SpikeAlerts.jsx     Anomaly notifications
│   ├── DistrictRestock.jsx Stock recommendations
│   ├── SummaryCards.jsx    KPI metrics
│   ├── ExportButton.jsx    CSV export
│   └── CsvPreviewModal.jsx Download preview
├── api.js                  Centralized API client
├── App.js                  Main routing
└── index.js                Entry point
```

---

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- MySQL 8+ (or SQLite for development)
- pip and npm

### Backend Setup

1. **Clone repository and navigate to project:**
   ```bash
   cd e:\technospice\project\healthcare-ai
   ```

2. **Create Python virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create `.env` file in project root:
   ```
   DB_NAME=healthcare_ai
   DB_USER=root
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=3306
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Import initial data:**
   ```bash
   python manage.py import_data
   ```

7. **Start Django development server:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Start React development server:**
   ```bash
   npm start
   ```

The frontend will open at `http://localhost:3000` and connect to backend at `http://localhost:8000`.

---

## Quick Start

### 1. Load Sample Data

```bash
# Import CSV data
python manage.py import_data

# Reset drug catalog
python manage.py reset_drug_master

# Generate daily appointments (triggers 30 appointments, prescriptions, stock updates)
python manage.py generate_daily_data

# Redistribute stock evenly across clinics
python manage.py redistribute_stock

# Update clinic addresses with Tamil Nadu districts
python manage.py update_clinic_addresses
```

### 2. Access the Application

- **Dashboard:** http://localhost:3000
- **Admin Panel:** http://localhost:3000/admin-panel
- **API:** http://localhost:8000/api/
- **Django Admin:** http://localhost:8000/admin/

### 3. Explore Features

- **View Disease Trends** — Dashboard filters by date range (1W-1Y)
- **Check Spike Alerts** — Historical context with statistical thresholds
- **Review Restock Suggestions** — District-level medicine recommendations
- **Export Data** — CSV downloads for analysis
- **Manage Data** — CRUD operations in admin panel

---

## API Endpoints

### Analytics Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|-----------|
| `/api/disease-trends/` | GET | Aggregate disease counts by type | `?days=30` |
| `/api/disease-trends/timeseries/` | GET | Daily disease counts over time | `?days=7&disease=Flu` |
| `/api/medicine-usage/` | GET | Medicine consumption by disease | `?days=30` |
| `/api/spike-alerts/` | GET | Detected outbreaks/anomalies | `?days=8&all=true` |
| `/api/restock-suggestions/` | GET | System-wide restock recommendations | `?days=30` |
| `/api/district-restock/` | GET | District-level stock suggestions | `?district=Chennai&days=30` |
| `/api/trend-comparison/` | GET | Period-over-period analysis | `?days=7` |
| `/api/top-medicines/` | GET | Highest usage drugs | `?days=30&limit=10` |
| `/api/seasonality/` | GET | Monthly disease patterns | `?days=365` |

### CRUD Endpoints

Full REST support (GET, POST, PUT, PATCH, DELETE) with pagination and search:

```
/api/crud/clinics/                [Full CRUD]
/api/crud/doctors/                [Full CRUD]
/api/crud/patients/               [Full CRUD]
/api/crud/diseases/               [Full CRUD]
/api/crud/appointments/           [Full CRUD]
/api/crud/drugs/                  [Full CRUD]
/api/crud/prescriptions/          [Full CRUD]
/api/crud/prescription-lines/     [Full CRUD]
/api/crud/dropdowns/              [GET only - dropdown options]
```

### CSV Export Endpoints

```
/api/export/disease-trends/    ?days=30
/api/export/spike-alerts/      ?days=8
/api/export/restock/           ?days=30
/api/export-report/            ?days=90
```

---

## Management Commands

### Data Import & Setup

```bash
# Import CSV data from data/ folder
python manage.py import_data

# Generate daily appointments (default: 30 appointments)
python manage.py generate_daily_data [--date=YYYY-MM-DD] [--appointments=N] [--spike="disease_name"]

# Reset drug catalog to 30 standard medicines
python manage.py reset_drug_master

# Evenly distribute stock across clinics
python manage.py redistribute_stock

# Update clinic addresses with Tamil Nadu districts
python manage.py update_clinic_addresses

# Inject spike for testing (historical date)
python manage.py inject_spike --disease="Influenza" --quantity=50

# Regenerate prescription lines after drug reset
python manage.py regenerate_prescription_lines
```

---

## Business Logic

### Disease Trend Analysis

Aggregates appointment counts by disease using ORM `Count()` aggregation (no Python loops):

```python
# Grouped by disease with metadata
SELECT disease.name, COUNT(*) as count
FROM appointments
WHERE appointment_datetime BETWEEN start AND end
GROUP BY disease.name
```

### Machine Learning Components

#### Moving Average Forecast
$$\text{Forecast} = (\text{avg\_last\_3\_days} \times 0.6) + (\text{avg\_last\_7\_days} \times 0.4)$$

- Last 3 days: 60% weight (captures recent trends)
- Last 7 days: 40% weight (smooths noise, provides stability)

#### Time Decay Weighting
$$\text{weighted\_trend} = (\text{recent\_count} \times 0.7) + (\text{older\_count} \times 0.3)$$

- Recent (last 7 days): 0.7 weight
- Older (days 8-30): 0.3 weight

#### Demand Prediction
$$\text{predicted\_demand} = \text{trend\_score} + \text{forecast}$$

Combines weighted historical trend with forward-looking forecast.

### Spike/Anomaly Detection

Statistical threshold using mean and standard deviation:

$$\text{is\_spike} = \text{today\_count} > (\mu + 2\sigma)$$

Where:
- $\mu$ = mean of last 7 days (excluding today)
- $\sigma$ = standard deviation of baseline
- **Threshold:** Mean + 2× Std Dev (95% confidence level)

Includes seasonal adjustment multipliers for in-season diseases.

### Intelligent Restock Calculator

Multi-factor algorithm considering:

1. **Expected Demand Calculation:**
   $$\text{expected\_demand} = \text{predicted\_demand} \times \text{avg\_usage} \times \text{safety\_buffer}$$

2. **Restock Quantity:**
   $$\text{suggested\_restock} = \max(0, \text{expected\_demand} - \text{current\_stock})$$

3. **Dynamic Safety Buffer:**
   $$\text{buffer} = 1.2 + (\text{spike\_ratio} \times 0.6)$$
   
   Higher spike ratio increases buffer to account for uncertainty

4. **Status Classification:**
   - `critical` — No stock or shortage > 50%
   - `low` — Partial shortage (20-50%)
   - `sufficient` — Stock meets expected demand

All calculations are **fully data-driven** with no hardcoded disease mappings.

### District-Level Filtering

All analytics endpoints support `?district=` parameter:
- Extracts district from clinic address (Tamil Nadu all 38 districts)
- Filters appointments and drug inventory by clinic location
- Delivers clinic-scoped recommendations

---

## Configuration

### Django Settings (config/settings.py)

Key configuration:
- `DEBUG = True` — Development mode (set to False in production)
- `ALLOWED_HOSTS = ['*']` — Allow all origins (restrict in production)
- `DATABASES` — MySQL connection via environment variables
- `INSTALLED_APPS` — Core, Analytics, Inventory, DataLoader apps
- `CORS_ALLOWED_ORIGINS` — Frontend at http://localhost:3000

### Environment Variables (.env)

```
DB_NAME=healthcare_ai
DB_USER=root
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=3306
DEBUG=True
SECRET_KEY=your-secret-key-min-50-chars
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Project Structure

```
healthcare-ai/
├── analytics/                    Intelligence layer
│   ├── models.py                Disease, Appointment models
│   ├── views.py                 Smart analytics endpoints
│   ├── crud_views.py            CRUD endpoints
│   ├── ml_engine.py             Forecasting algorithms
│   ├── spike_detector.py        Anomaly detection
│   ├── restock_calculator.py    Restocking logic
│   ├── aggregation.py           ORM aggregations
│   └── urls.py                  Route definitions
├── core/                         Domain models
│   ├── models.py                Clinic, Doctor, Patient
│   └── admin.py                 Admin interface
├── inventory/                    Stock management
│   ├── models.py                DrugMaster, Prescription, PrescriptionLine
│   └── admin.py                 Admin interface
├── data_loader/                  Data synchronization
│   └── management/commands/
│       ├── import_data.py        CSV import
│       ├── generate_daily_data.py Daily data generation
│       ├── reset_drug_master.py
│       ├── redistribute_stock.py
│       ├── update_clinic_addresses.py
│       ├── inject_spike.py
│       └── regenerate_prescription_lines.py
├── config/                       Project settings
│   ├── settings.py              Configuration
│   ├── urls.py                  URL routing
│   ├── asgi.py                  ASGI config
│   └── wsgi.py                  WSGI config
├── frontend/                     React application
│   ├── src/
│   │   ├── pages/               Main routes
│   │   ├── components/          React components
│   │   ├── api.js               API client
│   │   └── App.js               Main component
│   └── package.json             Dependencies
├── data/                         CSV data files
│   ├── Clinic.csv
│   ├── Doctor.csv
│   ├── Patient.csv
│   ├── Disease.csv
│   ├── Appointment.csv
│   ├── Prescription.csv
│   └── PrescriptionLine.csv
├── manage.py                     Django CLI
├── requirements.txt              Python dependencies
└── db.sqlite3                    Development database
```

---

## Data Flow

```
CSV Files (data/*.csv)
    ↓
Management Commands (data_loader)
    ├── import_data.py
    ├── generate_daily_data.py (daily sync)
    └── utility commands
    ↓
MySQL Database
    ├── Core: Clinic, Doctor, Patient
    ├── Analytics: Disease, Appointment
    └── Inventory: DrugMaster, Prescription, PrescriptionLine
    ↓
Django REST APIs (analytics/views.py)
    ├── Layer 1: ORM Aggregation
    ├── Layer 2: Time-Series Processing
    ├── Layer 3: ML Forecasting
    ├── Layer 4: Spike Detection
    ├── Layer 5: Restock Calculation
    └── Layer 6: CSV Export
    ↓
React Frontend (frontend/src/)
    ├── Dashboard (TrendChart, SpikeAlerts, DistrictRestock, SummaryCards)
    ├── Reports (CSV export)
    └── Admin Panel (CRUD management)
```

---

## Performance Optimizations

1. **ORM-Only Aggregation** — Use Django ORM `Count()`, `Sum()`, `Avg()` for all counting (no Python loops)
2. **Eager Loading** — `select_related()` for FK relationships to minimize database queries
3. **Native Grouping** — `TruncDate()`, `TruncMonth()` for database-level grouping
4. **Bulk Operations** — `bulk_create(batch_size=1000)` for imports
5. **Indexed Fields** — Frequent filters indexed (appointment_datetime, disease, clinic)
6. **Query Caching** — Django view-level caching available via `django.core.cache`
7. **Frontend Optimization** — Memoized API calls, Recharts efficient rendering

---

## Development Workflow

### 1. Start Development Servers

**Terminal 1 — Backend:**
```bash
cd e:\technospice\project\healthcare-ai
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 — Frontend:**
```bash
cd e:\technospice\project\healthcare-ai\frontend
npm start
```

### 2. Generate Test Data

```bash
python manage.py import_data          # Load initial dataset
python manage.py generate_daily_data --spike="Influenza_1" --appointments=50  # Inject spike
python manage.py redistribute_stock   # Even distribution
```

### 3. Monitor & Debug

- **API Testing:** Use Postman/Insomnia to test `/api/` endpoints
- **Django ORM Shell:**
  ```bash
  python manage.py shell
  from analytics.models import Appointment
  Appointment.objects.count()  # Check data
  ```
- **Frontend Console:** Browser DevTools for React/API debugging
- **Database Inspection:** Use MySQL Workbench or TablePlus

---

## API Usage Examples

### Get Disease Trends (Last 30 Days)

```bash
curl http://localhost:8000/api/disease-trends/?days=30
```

Response:
```json
[
  {
    "disease__name": "Influenza",
    "count": 156,
    "season": "winter",
    "severity": "high"
  },
  {
    "disease__name": "Malaria",
    "count": 89,
    "season": "monsoon",
    "severity": "medium"
  }
]
```

### Get Spike Alerts

```bash
curl http://localhost:8000/api/spike-alerts/?days=8
```

Response:
```json
[
  {
    "disease": "Dengue",
    "today_count": 25,
    "mean_last_7_days": 8.5,
    "std_dev": 2.1,
    "threshold": 12.7,
    "is_spike": true,
    "reason": "Statistical anomaly detected"
  }
]
```

### Get Restock Suggestions

```bash
curl http://localhost:8000/api/district-restock/?district=Chennai&days=30
```

Response:
```json
[
  {
    "drug_name": "Paracetamol",
    "current_stock": 45,
    "expected_demand": 120,
    "suggested_restock": 75,
    "status": "low",
    "clinic": "Chennai General Hospital"
  }
]
```

### Export Disease Trends as CSV

```bash
curl http://localhost:8000/api/export/disease-trends/?days=30 -o disease_trends.csv
```

---

## Troubleshooting

### Database Connection Error

**Problem:** `django.db.utils.OperationalError: (1045, "Access denied...")`

**Solution:**
1. Verify MySQL is running: `mysql -u root -p` enters MySQL shell
2. Check `.env` credentials: DB_USER, DB_PASSWORD, DB_HOST
3. Ensure database exists: `CREATE DATABASE healthcare_ai;`

### Frontend Cannot Connect to Backend

**Problem:** CORS errors in browser console

**Solution:**
1. Backend running on `http://localhost:8000`
2. Frontend running on `http://localhost:3000`
3. Check `CORS_ALLOWED_ORIGINS` in `config/settings.py`

### No Data in Dashboard

**Problem:** Empty trends/restock tables

**Solution:**
```bash
python manage.py import_data              # Load CSV data
python manage.py reset_drug_master        # Initialize drugs
python manage.py generate_daily_data      # Create appointments
python manage.py redistribute_stock       # Populate stock
```

### Slow Queries

**Problem:** API endpoints returning slowly

**Solution:**
1. Check database indexes: `SHOW KEYS FROM appointments;`
2. Use Django Debug Toolbar: `pip install django-debug-toolbar`
3. Enable query logging in `config/settings.py`

---

## Dependencies

### Python (requirements.txt)
- Django==6.0.3
- djangorestframework
- django-cors-headers
- mysql-connector-python
- pandas
- numpy
- python-decouple

### Node.js (frontend/package.json)
- react@18+
- axios
- recharts
- react-router-dom

---

## Production Deployment

### Before Going Live

1. **Update Django Settings:**
   - Set `DEBUG = False`
   - Update `SECRET_KEY` to random 50+ character string
   - Set `ALLOWED_HOSTS` to actual domain names
   - Update database credentials

2. **Security:**
   - Use HTTPS/SSL certificates
   - Set `SECURE_SSL_REDIRECT = True`
   - Enable `SECURE_HSTS_SECONDS`
   - Use environment variables for secrets

3. **Database:**
   - Use managed MySQL service (AWS RDS, Azure Database)
   - Enable automated backups
   - Set up read replicas for scaling

4. **Frontend:**
   - Run `npm run build` to create production bundle
   - Serve via Nginx/Apache with gzip compression
   - Enable caching headers

5. **Monitoring:**
   - Set up error tracking (Sentry)
   - Enable application performance monitoring (New Relic/DataDog)
   - Configure log aggregation (ELK Stack)

---

## License

Proprietary software for Tamil Nadu healthcare network analytics. All rights reserved.

---

## Support & Contact

For issues, questions, or feature requests, please reach out to the development team.

---
