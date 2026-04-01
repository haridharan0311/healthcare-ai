"""
Database optimization script - adds missing indexes for faster queries.
This improves query performance for common filters used in the analytics APIs.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Add indexes to improve query performance'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            indices = [
                # For appointment queries filtering by date range
                ('CREATE INDEX IF NOT EXISTS idx_appointment_datetime ON analytics_appointment(appointment_datetime);', 
                 'appointment_datetime index'),
                
                # For appointment queries filtering by disease
                ('CREATE INDEX IF NOT EXISTS idx_appointment_disease_id ON analytics_appointment(disease_id);', 
                 'appointment_disease_id index'),
                
                # For appointment queries by clinic
                ('CREATE INDEX IF NOT EXISTS idx_appointment_clinic_id ON analytics_appointment(clinic_id);', 
                 'appointment_clinic_id index'),
                
                # For prescription queries filtering by date
                ('CREATE INDEX IF NOT EXISTS idx_prescription_date ON inventory_prescription(prescription_date);',
                 'prescription_date index'),
                
                # For prescription line queries
                ('CREATE INDEX IF NOT EXISTS idx_prescriptionline_disease_id ON inventory_prescriptionline(disease_id);',
                 'prescriptionline_disease_id index'),
                
                # Composite indexes for common query patterns
                ('CREATE INDEX IF NOT EXISTS idx_appt_date_disease ON analytics_appointment(appointment_datetime, disease_id);',
                 'appointment datetime+disease composite index'),
                
                ('CREATE INDEX IF NOT EXISTS idx_rx_date_drug ON inventory_prescriptionline(prescription_id, drug_id);',
                 'prescriptionline prescription+drug composite index'),
            ]
            
            for sql, description in indices:
                try:
                    cursor.execute(sql)
                    self.stdout.write(self.style.SUCCESS(f'✓ Created {description}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠ Index maybe already exists or error: {description} - {e}'))
            
            self.stdout.write(self.style.SUCCESS('\n✓ Database optimization complete'))
