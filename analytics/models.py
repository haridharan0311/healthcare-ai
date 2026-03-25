from django.db import models


class Disease(models.Model):
    name = models.CharField(max_length=255, unique=True)

    # seasonality (critical for your project requirement)
    season = models.CharField(max_length=50, db_index=True)

    # optional classification (helps grouping in analytics)
    category = models.CharField(max_length=100, blank=True, null=True)

    # severity helps in prioritization (restock logic)
    severity = models.IntegerField(default=1)

    # active flag for future control
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField()

    def __str__(self):
        return self.name


class Appointment(models.Model):
    appointment_datetime = models.DateTimeField()

    appointment_status = models.CharField(max_length=50)

    disease = models.ForeignKey(
        'analytics.Disease',
        on_delete=models.CASCADE,
        db_index=True
    )

    clinic = models.ForeignKey(
        'core.Clinic',
        on_delete=models.CASCADE,
        db_index=True
    )

    doctor = models.ForeignKey(
        'core.Doctor',
        on_delete=models.CASCADE,
        db_index=True
    )

    patient = models.ForeignKey(
        'core.Patient',
        on_delete=models.CASCADE,
        db_index=True
    )

    op_number = models.CharField(max_length=50, db_index=True)

    def __str__(self):
        return f"{self.op_number} - {self.appointment_datetime}"



