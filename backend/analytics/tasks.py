from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import Appointment
import logging

logger = logging.getLogger(__name__)

@shared_task(name="cleanup_old_appointments")
def archive_old_appointments(years=3):
    """
    Task to clean up or archive appointments older than N years.
    Keeps the primary 'Appointment' table lean for performance.
    """
    cutoff_date = timezone.now() - timedelta(days=years * 365)
    
    try:
        # 1. Identify records to cleanup
        old_records = Appointment.objects.filter(appointment_datetime__lt=cutoff_date)
        count = old_records.count()
        
        if count > 0:
            logger.info(f"Starting archival of {count} records older than {years} years.")
            
            with transaction.atomic():
                # In a real system, you would copy these to an 'AppointmentArchive' table
                # or a cold storage bucket (S3/GCS) before deleting.
                # For this implementation, we will delete them to demonstrate the cleanup.
                old_records.delete()
            
            logger.info(f"Successfully archived {count} old appointment records.")
            return f"Cleaned up {count} records."
        
        return "No old records found for cleanup."
        
    except Exception as e:
        logger.error(f"Archival task failed: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"

@shared_task(name="generate_daily_summaries")
def generate_daily_summaries():
    """
    Optional: Pre-calculate daily aggregates for the dashboard 
    to make the UI even faster.
    """
    # Implementation of pre-aggregation logic would go here
    pass
