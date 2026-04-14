"""
LIVE DATA GENERATOR
===================
Generates realistic test data for development and testing purposes.

FEATURES:
- Automatically creates appointments, prescriptions, and related data
- Runs as background daemon thread (non-blocking)
- Season-aware disease weighting (monsoon diseases more common in monsoon)
- Realistic drug stock depletion
- Compatible with existing database schema

CONFIGURATION:
- ENABLE_LIVE_DATA_GENERATOR (default: True in DEBUG mode, False in PRODUCTION)
- LIVE_DATA_INTERVAL (default: 60 seconds between data generation cycles)

USAGE:
- Starts automatically when Django boots (see analytics/apps.py)
- Can be disabled by setting ENABLE_LIVE_DATA_GENERATOR=False in settings.py
- Run tests: python manage.py test analytics.tests.test_live_data_generator

EXAMPLE OUTPUT PER CYCLE:
- 1-3 new appointments (varies randomly)
- 0-2 new prescriptions (80% of completed appointments)
- 0-6 prescription line items
- Drug stock updates

THREAD SAFETY:
- Uses transaction.atomic() for database consistency
- Daemon thread automatically terminates on app shutdown
"""

import threading
import time
import random
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from django.db import transaction
from django.db.utils import OperationalError
from django.utils import timezone
from django.db.models import Max
from django.conf import settings

from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic

logger = logging.getLogger(__name__)


class LiveDataGenerator:
    """Background task to generate live data for dashboard."""
    
    def __init__(self):
        self.thread = None
        self.running = False
        self.interval = getattr(settings, 'LIVE_DATA_INTERVAL', 60)
        self.enabled = getattr(settings, 'ENABLE_LIVE_DATA_GENERATOR', settings.DEBUG)
        
    def start(self, interval=None):
        """Start the background data generation thread."""
        if interval:
            self.interval = interval
            
        if self.running:
            logger.warning('Live data generator already running')
            return
            
        self.running = True
        self.thread = threading.Thread(daemon=True, target=self._run_loop)
        self.thread.start()
        logger.info(f'✓ Live data generator started (interval: {self.interval}s)')
    
    def stop(self):
        """Stop the background thread."""
        self.running = False
        # Don't join(timeout) here as it might block the main thread unnecessarily
        logger.info('Live data generator stopping...')
    
    def get_status(self):
        """Return the current status of the generator."""
        return {
            'running': self.running and self.thread and self.thread.is_alive(),
            'interval': self.interval,
            'enabled': self.enabled
        }

    def _run_loop(self):
        """Main loop that generates data every N seconds (dynamic interval)."""
        try:
            time.sleep(2)  # Short wait for startup
            
            while self.running:
                try:
                    self.generate_data()
                except Exception as e:
                    logger.error(f'Error generating live data: {e}', exc_info=True)
                
                # Sleep in small increments to respond faster to stop()
                current_sleep = 0
                while current_sleep < self.interval and self.running:
                    time.sleep(1)
                    current_sleep += 1
                    
        except Exception as e:
            logger.error(f'Live data generator fatal error: {e}', exc_info=True)
            self.running = False
    
    def generate_data(self):
        """Generate a batch of appointments, prescriptions, and related data."""
        
        # ── Load reference data ──────────────────────────────────
        clinics = list(Clinic.objects.all())
        doctors = list(Doctor.objects.all())
        patients = list(Patient.objects.all())
        diseases = list(Disease.objects.filter(is_active=True))
        drugs = list(DrugMaster.objects.all())
        
        if not all([clinics, doctors, patients, diseases, drugs]):
            logger.warning('Missing reference data for live generation')
            return
        
        # ── Pre-group by clinic for speed ────────────────────────
        doctors_by_clinic = defaultdict(list)
        for d in doctors:
            doctors_by_clinic[d.clinic_id].append(d)
        
        patients_by_clinic = defaultdict(list)
        for p in patients:
            patients_by_clinic[p.clinic_id].append(p)
        
        drugs_by_clinic = defaultdict(list)
        for d in drugs:
            drugs_by_clinic[d.clinic_id].append(d)
        
        # ── Season-aware disease weights ─────────────────────────
        today = timezone.now().date()
        month = today.month
        season_map = {
            'Summer': [3, 4, 5, 6],
            'Monsoon': [7, 8, 9, 10],
            'Winter': [11, 12, 1, 2],
        }
        
        def get_weight(d):
            for season, months in season_map.items():
                if d.season == season and month in months:
                    return 3
            return 1
        
        disease_weights = [get_weight(d) for d in diseases]
        
        # ── Get next OP number ───────────────────────────────────
        op_base = Appointment.objects.aggregate(max_op=Max('op_number'))['max_op'] or 'OP000000'
        try:
            op_counter = int(''.join(filter(str.isdigit, op_base))) + 1
        except Exception:
            op_counter = random.randint(100000, 999999)
        
        # ── Generate 1-3 appointments for this batch ─────────────
        num_appointments = random.randint(1, 3)
        appt_objs = []
        
        now = timezone.now()
        for _ in range(num_appointments):
            clinic = random.choice(clinics)
            doctor = random.choice(doctors_by_clinic[clinic.id] or doctors)
            patient = random.choice(patients_by_clinic[clinic.id] or patients)
            disease = random.choices(diseases, weights=disease_weights, k=1)[0]
            
            # Generate appointment in a random time window (past 30 mins to future 2 hours)
            offset = random.randint(-1800, 7200)  # -30min to +2hrs
            appt_dt = now + timedelta(seconds=offset)
            
            status = random.choices(['Completed', 'Scheduled', 'Cancelled'], weights=[70, 20, 10])[0]
            
            appt_objs.append(Appointment(
                appointment_datetime=appt_dt,
                appointment_status=status,
                disease=disease,
                clinic=clinic,
                doctor=doctor,
                patient=patient,
                op_number=f'OP{op_counter:06d}'
            ))
            op_counter += 1
        
        with transaction.atomic():
            created_appts = Appointment.objects.bulk_create(appt_objs)
        
        # Refresh appointments from DB to get their IDs (required for related objects)
        if created_appts:
            created_appts = list(Appointment.objects.filter(
                op_number__in=[a.op_number for a in created_appts]
            ))
        
        # ── Generate prescriptions for completed appointments ────
        # Use .create() instead of bulk_create() for better ID handling
        completed_appts = [a for a in created_appts if a.appointment_status == 'Completed']
        created_prescriptions = []
        
        for appt in completed_appts:
            if random.random() > 0.2:  # 80% get prescriptions
                rx = Prescription.objects.create(
                    prescription_date=appt.appointment_datetime.date(),
                    appointment=appt,
                    clinic=appt.clinic,
                    doctor=appt.doctor,
                    patient=appt.patient
                )
                created_prescriptions.append(rx)
        
        # ── Generate prescription lines & update stock ──────────
        prescription_lines = []
        drug_usage = defaultdict(int)
        
        for prescription in created_prescriptions:
            disease = prescription.appointment.disease
            available_drugs = drugs_by_clinic[prescription.clinic_id] or drugs
            num_drugs = min(random.randint(1, 3), len(available_drugs))
            chosen_drugs = random.sample(available_drugs, num_drugs)
            
            for drug in chosen_drugs:
                qty = random.choices([1, 2, 3], weights=[3, 2, 1])[0]
                duration_days = random.choice([3, 5, 7, 10, 14])
                
                prescription_lines.append(PrescriptionLine(
                    prescription=prescription,
                    prescription_date=prescription.prescription_date,
                    drug=drug,
                    disease=disease,
                    quantity=qty,
                    duration=f'{duration_days} days',
                    instructions=random.choice([
                        'Take after food', 'Take before food', 'Take with water',
                        'Take twice daily', 'Take at bedtime', 'Take as directed'
                    ])
                ))
                drug_usage[drug.id] += qty
        
        # ── Create prescription lines ─────────────────────────────
        if prescription_lines:
            max_retries = 4
            for attempt in range(1, max_retries + 1):
                try:
                    with transaction.atomic():
                        PrescriptionLine.objects.bulk_create(prescription_lines, batch_size=100)
                    break
                except OperationalError as exc:
                    error_code = exc.args[0] if exc.args else 0
                    # Retry on: 1205 (lock timeout) and 1213 (deadlock)
                    if error_code in (1205, 1213) and attempt < max_retries:
                        wait_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s, 8s
                        logger.warning(
                            f'Database lock issue (code {error_code}) during prescription lines create '
                            f'(attempt {attempt}/{max_retries}), retrying in {wait_time}s...'
                        )
                        time.sleep(wait_time)
                        continue
                    logger.error('Prescription lines bulk create failed', exc_info=exc)
                    break
                except Exception as exc:
                    logger.error('Prescription lines bulk create failed', exc_info=exc)
                    break

        # ── Update drug stock ────────────────────────────────────
        if drug_usage:
            max_retries = 4
            for attempt in range(1, max_retries + 1):
                try:
                    with transaction.atomic():
                        drug_objs = DrugMaster.objects.filter(id__in=drug_usage.keys())
                        for d in drug_objs:
                            d.current_stock = max(0, d.current_stock - drug_usage[d.id])
                        DrugMaster.objects.bulk_update(drug_objs, ['current_stock'], batch_size=200)
                    break
                except OperationalError as exc:
                    error_code = exc.args[0] if exc.args else 0
                    # Retry on: 1205 (lock timeout) and 1213 (deadlock)
                    if error_code in (1205, 1213) and attempt < max_retries:
                        wait_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s, 8s
                        logger.warning(
                            f'Database lock issue (code {error_code}) during drug stock update '
                            f'(attempt {attempt}/{max_retries}), retrying in {wait_time}s...'
                        )
                        time.sleep(wait_time)
                        continue
                    logger.error('Drug stock bulk update failed', exc_info=exc)
                    break
                except Exception as exc:
                    logger.error('Drug stock bulk update failed', exc_info=exc)
                    break

        # ── Log summary ──────────────────────────────────────────
        total_lines = len(prescription_lines)
        logger.info(
            f'Live data generated: {len(created_appts)} appts, '
            f'{len(created_prescriptions)} rx, {total_lines} lines'
        )


# Global instance
_generator = LiveDataGenerator()


def start_live_data_generator():
    """Start the live data generator (called from AppConfig.ready())."""
    _generator.start()


def stop_live_data_generator():
    """Stop the live data generator."""
    _generator.stop()

