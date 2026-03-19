from rest_framework import serializers

from .models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic



class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = ['id', 'name', 'season', 'category', 'severity', 'is_active']


class DrugMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugMaster
        fields = ['id', 'drug_name', 'generic_name', 'drug_strength', 'dosage_type']


class PrescriptionLineSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.drug_name', read_only=True)
    disease_name = serializers.CharField(source='disease.name', read_only=True)

    class Meta:
        model = PrescriptionLine
        fields = ['id', 'drug_name', 'disease_name', 'quantity', 'duration', 'instructions']


class AppointmentSerializer(serializers.ModelSerializer):
    disease_name = serializers.CharField(source='disease.name', read_only=True)
    disease_season = serializers.CharField(source='disease.season', read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_datetime', 'appointment_status',
            'disease_name', 'disease_season',
            'patient_name', 'doctor_name', 'op_number'
        ]

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_doctor_name(self, obj):
        last = obj.doctor.last_name or ''
        return f"{obj.doctor.first_name} {last}".strip()


# --- Analytics-specific output serializers (not tied to a model) ---
# These are used to shape the JSON responses from your API views.

class DiseaseTrendSerializer(serializers.Serializer):
    disease_name = serializers.CharField()
    season = serializers.CharField()
    total_cases = serializers.IntegerField()
    trend_score = serializers.FloatField()
    seasonal_weight = serializers.FloatField()


class TimeSeriesPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    disease_name = serializers.CharField()
    case_count = serializers.IntegerField()


class SpikeAlertSerializer(serializers.Serializer):
    disease_name = serializers.CharField()
    today_count = serializers.IntegerField()
    mean_last_7_days = serializers.FloatField()
    std_dev = serializers.FloatField()
    threshold = serializers.FloatField()
    is_spike = serializers.BooleanField()


class RestockSuggestionSerializer(serializers.Serializer):
    drug_name = serializers.CharField()
    generic_name = serializers.CharField()
    current_stock = serializers.IntegerField()
    predicted_demand = serializers.FloatField()
    suggested_restock = serializers.IntegerField()
    status = serializers.CharField()  # e.g., "OK", "Low Stock", "Critical"
    contributing_diseases = serializers.ListField(child=serializers.CharField())
