# Live Data Generator

## Overview

The **Live Data Generator** automatically creates realistic medical data (appointments, patients, prescriptions, etc.) every 30 seconds while running the Django development server. This is perfect for:

- Testing a live dashboard with fresh data
- Demonstrating real-time features
- Load testing
- Demo purposes

## How It Works

When you run `python manage.py runserver`, the generator:

1. Starts automatically (if `DEBUG=True` and enabled)
2. Runs in a background daemon thread (non-blocking)
3. Every 30 seconds, generates:
   - 1-3 new appointments with random clinics, doctors, patients, diseases
   - Prescriptions for completed appointments (80% chance)
   - Prescription lines with realistic medicine usage
   - Updates drug stock counts automatically
4. Uses season-aware disease weighting (monsoon diseases more common in monsoon, etc.)

## Configuration

In `config/settings.py`:

```python
# Enable/disable the generator
ENABLE_LIVE_DATA_GENERATOR = DEBUG  # Only in dev (default: True if DEBUG=True)

# Interval between data generations (seconds)
LIVE_DATA_INTERVAL = 30  # Default: 30 seconds
```

### Disable for a specific run:

```python
# Add to settings.py or .env
ENABLE_LIVE_DATA_GENERATOR = False
```

Or modify `config/settings.py`:

```python
ENABLE_LIVE_DATA_GENERATOR = False  # Disable generator
LIVE_DATA_INTERVAL = 60  # Or change interval to 60 seconds
```

## Usage

### Start with live data generation (Default)

```bash
python manage.py runserver
```

![Example output in server logs]:
```
✓ Live data generator started (interval: 30s)
Live data generated: 2 appts, 1 rx, 2 lines
Live data generated: 3 appts, 2 rx, 5 lines
```

### Disable for a run

Set in `config/settings.py`:

```python
ENABLE_LIVE_DATA_GENERATOR = False
```

Or create `.env` file:

```bash
ENABLE_LIVE_DATA_GENERATOR=False
```

And update `config/settings.py` to use it:

```python
from decouple import config

ENABLE_LIVE_DATA_GENERATOR = config('ENABLE_LIVE_DATA_GENERATOR', default=DEBUG, cast=bool)
```

### Change generation interval

```python
# Generate every 60 seconds instead of 30
LIVE_DATA_INTERVAL = 60
```

## What Gets Generated

Each 30-second cycle generates:

### Appointments
- 1-3 appointments per cycle
- Random clinic, doctor, patient from database
- Random disease (season-aware weighting)
- Status: 70% Completed, 20% Scheduled, 10% Cancelled
- OP number auto-incremented

### Prescriptions
- Generated for 80% of completed appointments
- Links to appointment, clinic, doctor, patient

### Prescription Lines
- 1-3 medicines per prescription
- Random quantity (1-3 units)
- Duration: 3, 5, 7, 10, 14 days
- Random instructions

### Stock Updates
- Drug stock decremented based on prescription quantities
- Never goes below 0

## Logging

View detailed logs:

```bash
# In Django console output:
Live data generated: 2 appts, 1 rx, 5 lines

# If errors occur:
ERROR: Error generating live data: [error details]
```

To enable debug logging in `config/settings.py`:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'analytics.live_data_generator': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

## Stopping the Generator

The generator stops automatically when:
- Django server shuts down
- You press Ctrl+C
- All background threads terminate

## Performance Impact

- **Minimal**: Runs in a daemon thread, doesn't block request handling
- **Database load**: ~3-5 queries per cycle (1-3 appointments + prescriptions + stock updates)
- **CPU**: Negligible (idle between cycles)
- **Memory**: ~10-50MB for thread + data

## Troubleshooting

### Generator not starting?

1. Check if `DEBUG=True` in `settings.py`
2. Check if `ENABLE_LIVE_DATA_GENERATOR` is not explicitly `False`
3. Check console logs for errors
4. Ensure reference data exists (clinics, doctors, patients, diseases, drugs)

### Not seeing data in dashboard?

1. Verify reference data exists (check Django admin or database)
2. Check that your API endpoints are reading fresh data (not from cache)
3. Refresh the frontend/dashboard page
4. Check database logs

### Performance is slow?

1. Increase `LIVE_DATA_INTERVAL` to 60+ seconds
2. Disable generator during testing: set `ENABLE_LIVE_DATA_GENERATOR = False`
3. Check database connection and performance

## Architecture

**File**: `analytics/live_data_generator.py`
- `LiveDataGenerator` class manages thread lifecycle
- `start_live_data_generator()` starts the background task
- Called from `analytics/apps.py` in the `AppConfig.ready()` method

**Flow**:
```
Django starts
  ↓
AppConfig.ready() called
  ↓
start_live_data_generator()
  ↓
Background thread starts (daemon)
  ↓
Every 30 seconds → generate_data()
  ↓
Creates appointments, prescriptions, lines
  ↓
Updates drug stock
```

## Production

⚠️ **The generator only runs when `DEBUG=True`**, so it's safe to leave enabled in production code (it will be disabled in production since `DEBUG=False`).

To be extra safe, explicitly set:

```python
# config/settings.py
if DEBUG:
    ENABLE_LIVE_DATA_GENERATOR = True
else:
    ENABLE_LIVE_DATA_GENERATOR = False
```

## API Integration

The generator uses the same data models used throughout your app:
- `analytics.models.Appointment`
- `core.models.Patient, Doctor, Clinic`
- `inventory.models.Prescription, PrescriptionLine, DrugMaster`

All generated data is immediately available through your existing APIs:
- `/api/disease-trends/`
- `/api/reports/weekly/`
- `/api/reports/monthly/`
- `/api/restock/district-restock/`
- etc.

---

**Created**: 01 Apr 2026  
**Last Updated**: 01 Apr 2026
