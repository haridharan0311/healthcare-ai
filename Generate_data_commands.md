# ── Basic usage ──────────────────────────────────────────────────────

# Generate data for TODAY (default 30 appointments)
python manage.py generate_daily_data

# Generate data for a SPECIFIC DATE
python manage.py generate_daily_data --date 2026-03-20

# ── Control appointment count ────────────────────────────────────────

# Light day — 15 appointments
python manage.py generate_daily_data --date 2026-03-20 --appointments 15

# Normal day — 30 appointments (default)
python manage.py generate_daily_data --date 2026-03-20 --appointments 30

# Busy day — 60 appointments
python manage.py generate_daily_data --date 2026-03-20 --appointments 60

# ── Spike injection ──────────────────────────────────────────────────

# Spike Flu on a specific date (adds 22–32 extra Flu cases)
python manage.py generate_daily_data --date 2026-03-21 --spike Flu

# Spike COVID-19
python manage.py generate_daily_data --date 2026-03-22 --spike COVID-19

# Spike Diabetes
python manage.py generate_daily_data --date 2026-03-23 --spike Diabetes

# Spike Asthma
python manage.py generate_daily_data --date 2026-03-24 --spike Asthma

# ── Combine all options ───────────────────────────────────────────────

# Busy day + spike
python manage.py generate_daily_data --date 2026-03-25 --appointments 50 --spike Flu

# Light day + spike (spike will dominate — good for demo)
python manage.py generate_daily_data --date 2026-03-16 --appointments 55 --spike COVID-19