"""
Live Data Generator for Development/Testing
=====================================
Generates realistic appointments, patients, prescriptions, and prescription lines
every 30 seconds to simulate a live dashboard with fresh data.

Usage: Starts automatically in Django's ready() method. Can be controlled via:
  - ENABLE_LIVE_DATA_GENERATOR setting (default: True in DEBUG mode)
  - LIVE_DATA_INTERVAL setting (default: 30 seconds)
"""

import threading
import time
import random
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from django.db import transaction
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
        self.interval = getattr(settings, 'LIVE_DATA_INTERVAL', 30)
        self.enabled = getattr(settings, 'ENABLE_LIVE_DATA_GENERATOR', settings.DEBUG)
        
    def start(self):
        """Start the background data generation thread."""
        if not self.enabled:
            logger.info('Live data generator is disabled')
            return
            
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
        if self.thread:
            self.thread.join(timeout=5)
        logger.info('Live data generator stopped')
    
    def _run_loop(self):
        """Main loop that generates data every N seconds."""
        try:
            time.sleep(5)  # Wait for Django to fully initialize
            
            while self.running:
                try:
                    self.generate_data()
                except Exception as e:
                    logger.error(f'Error generating live data: {e}', exc_info=True)
                
                time.sleep(self.interval)
        except Exception as e:
            logger.error(f'Live data generator fatal error: {e}', exc_info=True)
            self.running = False
    
    @transaction.atomic
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
        
        # Use batch_size to handle larger datasets safely
        if prescription_lines:
            PrescriptionLine.objects.bulk_create(prescription_lines, batch_size=100)
        
        # ── Update drug stock ────────────────────────────────────
        if drug_usage:
            drug_objs = DrugMaster.objects.filter(id__in=drug_usage.keys())
            for d in drug_objs:
                d.current_stock = max(0, d.current_stock - drug_usage[d.id])
            DrugMaster.objects.bulk_update(drug_objs, ['current_stock'], batch_size=200)
        
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
