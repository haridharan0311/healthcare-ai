# Serializers package — re-exports for clean imports across the app

from analytics.serializers.serializers import (
    AppointmentSerializer,
    DiseaseTrendSerializer,
    SpikeAlertSerializer,
    RestockSuggestionSerializer,
)

from analytics.serializers.crud_serializers import (
    ClinicSerializer,
    DoctorSerializer,
    PatientSerializer,
    DiseaseSerializer,
    DrugMasterSerializer,
    PrescriptionSerializer,
    PrescriptionLineSerializer,
)
