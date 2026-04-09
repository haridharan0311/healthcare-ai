from django.contrib import admin

from .models import Prescription, PrescriptionLine, DrugMaster

admin.site.register(Prescription)
admin.site.register(PrescriptionLine)
admin.site.register(DrugMaster)