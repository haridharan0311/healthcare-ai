from django.db import models
from django.contrib.auth.models import User

class Clinic(models.Model):
    clinic_name = models.CharField(max_length=255)
    clinic_address_1 = models.TextField()

    def __str__(self):
        return self.clinic_name

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Super Admin'),
        ('CLINIC_USER', 'Clinic User'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Doctor(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('U', 'Unknown'),
    )

    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    qualification = models.CharField(max_length=255)

    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name='doctors'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()


class Patient(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('U', 'Unknown'),
    )

    TITLE_CHOICES = (
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
        ('Mrs', 'Mrs'),
        ('Dr', 'Dr'),
    )

    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    title = models.CharField(max_length=10, choices=TITLE_CHOICES)

    dob = models.DateField()
    mobile_number = models.CharField(max_length=15, db_index=True)

    address_line_1 = models.TextField()

    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name='patients'
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

