# Healthcare AI Platform

A robust Django + Channels backend for predictive disease analytics, real-time outbreak detection, and intelligent inventory management.

## 🚀 Quickstart

1. **Navigate to backend**: `cd backend`
2. **Activate Environment**: `..\.venv\Scripts\activate` (Windows)
3. **Run Server**: `python manage.py runserver`

## 📡 Core Architecture

The system uses standard REST APIs (`/api/`) and real-time WebSockets (`/ws/`) powered by a centralized Service Layer.

### REST API Endpoints
- **Disease Analytics**: `/api/disease-trends/`, `/api/disease-seasonality/`, `/api/trend-comparison/`
- **Inventory/Restock**: `/api/restock/`, `/api/top-medicines/`, `/api/low-stock-alerts/`
- **Spike Detection**: `/api/spike-alerts/`
- **Reporting**: `/api/reports/weekly/`, `/api/reports/monthly/`, `/api/exports/...`

### WebSockets (Live Data)
Connections automatically receive initial state upon connection, followed by real-time push updates.
- **`ws://localhost:8000/ws/disease-trends/`**: Live case tracking.
- **`ws://localhost:8000/ws/spike-alerts/`**: Immediate outbreak anomaly alerts.
- **`ws://localhost:8000/ws/restock/`**: Live inventory depletion warnings.

## 🛠 Project Structure
- `backend/analytics/`: Business logic (Service Layer), ML models, and Channels Consumers.
- `backend/inventory/`: Medicine, stock levels, and prescription tracking.
- `backend/core/`: Central entities (Patients, Doctors, Clinics).
- `backend/data_loader/`: Data seeding utilities (See `DATA_LOADER.md` for CLI commands).
