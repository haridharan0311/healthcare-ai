from django.db import models

class Disease(models.Model):
    """
    Represents a specific disease or clinical condition.
    Used for tracking outbreaks, seasonality, and medicine efficacy.
    """
    
    SEASON_CHOICES = (
        ('Summer', 'Summer'),
        ('Monsoon', 'Monsoon'),
        ('Winter', 'Winter'),
        ('All', 'All-Year'),
        ('Unknown', 'Unknown'),
    )

    name = models.CharField(max_length=255, unique=True, db_index=True)

    # Seasonality (critical for outbreak detection and forecasting)
    season = models.CharField(
        max_length=50, 
        choices=SEASON_CHOICES, 
        default='All',
        db_index=True
    )

    # Optional classification (helps grouping in dashboard analytics)
    category = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    # Severity helps in prioritization (restock logic and alert ranking)
    severity = models.IntegerField(default=1, help_text="Ranking from 1 (Low) to 5 (Critical)")

    # Active flag for system-wide control
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Disease Master"
        verbose_name_plural = "Diseases"
        ordering = ['name']

    def __str__(self):
        return self.name


class Appointment(models.Model):
    """
    Represents a clinical encounter.
    The primary transaction model for analytics, trends, and doctor performance.
    """
    
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    )

    appointment_datetime = models.DateTimeField(db_index=True)

    appointment_status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='COMPLETED',
        db_index=True
    )

    disease = models.ForeignKey(
        'analytics.Disease',
        on_delete=models.CASCADE,
        related_name='appointments',
        db_index=True
    )

    clinic = models.ForeignKey(
        'core.Clinic',
        on_delete=models.CASCADE,
        related_name='appointments',
        db_index=True
    )

    doctor = models.ForeignKey(
        'core.Doctor',
        on_delete=models.CASCADE,
        related_name='appointments',
        db_index=True
    )

    patient = models.ForeignKey(
        'core.Patient',
        on_delete=models.CASCADE,
        related_name='appointments',
        db_index=True
    )

    op_number = models.CharField(max_length=50, db_index=True)

    class Meta:
        verbose_name = "Clinical Appointment"
        verbose_name_plural = "Clinical Appointments"
        indexes = [
            # Compound index for dashboard queries (filtering by clinic and date)
            models.Index(fields=['clinic', 'appointment_datetime']),
            # Compound index for trend analysis
            models.Index(fields=['appointment_datetime', 'disease']),
            # Compound index for doctor performance
            models.Index(fields=['doctor', 'appointment_datetime']),
        ]
        ordering = ['-appointment_datetime']

    def __str__(self):
        return f"{self.op_number} - {self.appointment_datetime.date()}"


