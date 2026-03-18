from django.contrib import admin

from .models import Doctor, Patient, Clinic

admin.site.register(Clinic)
admin.site.register(Doctor)
admin.site.register(Patient)
