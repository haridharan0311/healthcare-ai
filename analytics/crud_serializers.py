from rest_framework import serializers

from .models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Clinic
        fields = '__all__'


class DoctorSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.clinic_name', read_only=True)

    class Meta:
        model  = Doctor
        fields = '__all__'


class PatientSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.clinic_name', read_only=True)
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model  = Patient
        fields = '__all__'

    def get_doctor_name(self, obj):
        if obj.doctor:
            return f"{obj.doctor.first_name} {obj.doctor.last_name or ''}".strip()
        return None


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Disease
        fields = '__all__'


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name  = serializers.SerializerMethodField()
    disease_name = serializers.CharField(source='disease.name', read_only=True)
    clinic_name  = serializers.CharField(source='clinic.clinic_name', read_only=True)

    class Meta:
        model  = Appointment
        fields = '__all__'

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name or ''}".strip()

    def validate_appointment_status(self, value):
        # Normalize to Title case to match existing DB values
        return value.strip().capitalize()


class DrugMasterSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.clinic_name', read_only=True)

    class Meta:
        model  = DrugMaster
        fields = '__all__'


class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name  = serializers.SerializerMethodField()
    clinic_name  = serializers.CharField(source='clinic.clinic_name', read_only=True)

    class Meta:
        model  = Prescription
        fields = '__all__'

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name or ''}".strip()


class PrescriptionLineSerializer(serializers.ModelSerializer):
    drug_name    = serializers.CharField(source='drug.drug_name', read_only=True)
    disease_name = serializers.CharField(source='disease.name', read_only=True)

    class Meta:
        model  = PrescriptionLine
        fields = '__all__'

