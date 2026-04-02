# Live Data Generator

Automatically generates realistic test data for development and testing.

## Quick Summary

- **Starts automatically** when Django boots (in DEBUG mode)
- **Generates data every 30 seconds** (configurable)
- **Creates**: Appointments, prescriptions, and drug usage
- **Disables in production** automatically

## Features

✅ Season-aware disease weighting (monsoon diseases more common in monsoon)  
✅ Realistic drug stock depletion  
✅ Valid FK relationships (all data is consistent)  
✅ Unique OP numbers for each appointment  
✅ 80% of completed appointments get prescriptions  
✅ 1-3 prescription lines per prescription  

## Configuration

Edit `config/settings.py`:

```python
# Enable/disable (default: True in DEBUG, False in PRODUCTION)
ENABLE_LIVE_DATA_GENERATOR = DEBUG

# How often to generate data (seconds)
LIVE_DATA_INTERVAL = 30
```

## Data Generated Per Cycle

Each 30-second cycle creates:
- **1-3 appointments** (random)
- **0-2 prescriptions** (80% of completed appointments)
- **0-6 prescription line items**
- **Drug stock updates** (decreases)

## Testing

Run live data generator tests:

```bash
python manage.py test analytics.tests.test_live_data_generator
```

Test coverage:
- ✓ Generator initialization
- ✓ Appointment creation
- ✓ Prescription creation
- ✓ Prescription line creation
- ✓ Valid FK relationships
- ✓ Drug stock depletion
- ✓ Unique OP numbers
- ✓ Status value validation

## Disabling

To disable in development:

```python
# In config/settings.py
ENABLE_LIVE_DATA_GENERATOR = False

# Or set in environment
DEBUG = False
```

## View Generated Data

```bash
# Watch appointments flow in (in admin or via API)
GET http://localhost:8000/api/appointments/

# Check appointments in Django admin
http://localhost:8000/admin/analytics/appointment/
```

## Troubleshooting

**Q: Not generating data?**  
A: Check `ENABLE_LIVE_DATA_GENERATOR = True` in settings.py and `DEBUG = True`

**Q: Stock going negative?**  
A: This is a known behavior in test data. Real system would have stock floors.

**Q: Too fast/slow?**  
A: Adjust `LIVE_DATA_INTERVAL` in settings.py (seconds)
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
