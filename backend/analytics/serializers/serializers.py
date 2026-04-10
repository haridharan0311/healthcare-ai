from rest_framework import serializers

from ..models import Disease, Appointment
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
    period_count = serializers.IntegerField()
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


class TrendComparisonSerializer(serializers.Serializer):
    disease_name  = serializers.CharField()
    season        = serializers.CharField()
    period1_count = serializers.IntegerField()
    period2_count = serializers.IntegerField()
    change        = serializers.IntegerField()
    pct_change    = serializers.FloatField()
    direction     = serializers.CharField()
    period1       = serializers.CharField()
    period2       = serializers.CharField()


class TopMedicineSerializer(serializers.Serializer):
    drug_name             = serializers.CharField()
    generic_name          = serializers.CharField()
    dosage_type           = serializers.CharField()
    total_quantity        = serializers.IntegerField()
    total_prescriptions   = serializers.IntegerField()
    avg_qty_per_rx        = serializers.FloatField()


class LowStockAlertSerializer(serializers.Serializer):
    drug_name    = serializers.CharField()
    generic_name = serializers.CharField()
    total_stock  = serializers.IntegerField()
    threshold    = serializers.IntegerField()
    alert_level  = serializers.CharField()
    restock_now  = serializers.BooleanField()


class DoctorTrendSerializer(serializers.Serializer):
    doctor_id    = serializers.IntegerField()
    doctor_name  = serializers.CharField()
    disease_name = serializers.CharField()
    season       = serializers.CharField()
    case_count   = serializers.IntegerField()


class WeeklyDataSerializer(serializers.Serializer):
    week         = serializers.CharField()
    disease_name = serializers.CharField()
    case_count   = serializers.IntegerField()


class MonthlyDataSerializer(serializers.Serializer):
    month        = serializers.CharField()
    disease_name = serializers.CharField()
    case_count   = serializers.IntegerField()


class MedicineUsageSerializer(serializers.Serializer):
    drug_name          = serializers.CharField()
    generic_name       = serializers.CharField()
    disease_name       = serializers.CharField()
    season             = serializers.CharField()
    total_quantity     = serializers.IntegerField()
    total_cases        = serializers.IntegerField()
    avg_usage          = serializers.FloatField()
    prescription_count = serializers.IntegerField()