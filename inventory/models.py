from django.db import models


class DrugMaster(models.Model):
    drug_name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True, null=True)
    drug_strength = models.CharField(max_length=100)
    dosage_type = models.CharField(max_length=100)

    current_stock = models.IntegerField(default=0)

    clinic = models.ForeignKey(
        'core.Clinic',
        on_delete=models.CASCADE,
        db_index=True
    )

    def __str__(self):
        return self.drug_name


class Prescription(models.Model):
    prescription_date = models.DateField()

    appointment = models.ForeignKey(
        'analytics.Appointment',
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

    def __str__(self):
        return f"Prescription {self.id} - {self.prescription_date}"


class PrescriptionLine(models.Model):
    duration = models.CharField(max_length=100)
    instructions = models.TextField()

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='lines',
        db_index=True
    )

    disease = models.ForeignKey(
        'analytics.Disease',
        on_delete=models.SET_NULL,
        null=True,
        db_index=True
    )

    quantity = models.IntegerField()

    drug = models.ForeignKey(
        DrugMaster,
        on_delete=models.CASCADE,
        db_index=True
    )

    def __str__(self):
        return f"{self.drug} - {self.quantity}"