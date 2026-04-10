from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.cache import cache_page


from ..models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Patient, Doctor, Clinic

from ..serializers.crud_serializers import (
    ClinicSerializer, DoctorSerializer, PatientSerializer,
    DiseaseSerializer, AppointmentSerializer, DrugMasterSerializer,
    PrescriptionSerializer, PrescriptionLineSerializer
)


class StandardPagination(PageNumberPagination):
    page_size            = 20
    page_size_query_param = 'page_size'
    max_page_size        = 100


class ClinicViewSet(viewsets.ModelViewSet):
    queryset         = Clinic.objects.all().order_by('id')
    serializer_class = ClinicSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['clinic_name']
    ordering_fields  = ['id', 'clinic_name']


class DoctorViewSet(viewsets.ModelViewSet):
    queryset         = Doctor.objects.select_related('clinic').all().order_by('id')
    serializer_class = DoctorSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['first_name', 'last_name', 'qualification']
    ordering_fields  = ['id', 'first_name']


class PatientViewSet(viewsets.ModelViewSet):
    queryset         = Patient.objects.select_related('clinic', 'doctor').all().order_by('id')
    serializer_class = PatientSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['first_name', 'last_name', 'mobile_number']
    ordering_fields  = ['id', 'first_name']


class DiseaseViewSet(viewsets.ModelViewSet):
    queryset         = Disease.objects.all().order_by('id')
    serializer_class = DiseaseSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['name', 'season', 'category']
    ordering_fields  = ['id', 'name', 'severity']


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset         = Appointment.objects.select_related(
                           'clinic', 'doctor', 'patient', 'disease'
                       ).all().order_by('-appointment_datetime')
    serializer_class = AppointmentSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['op_number', 'appointment_status']
    ordering_fields  = ['id', 'appointment_datetime']


class DrugMasterViewSet(viewsets.ModelViewSet):
    queryset         = DrugMaster.objects.select_related('clinic').all().order_by('id')
    serializer_class = DrugMasterSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['drug_name', 'generic_name', 'dosage_type']
    ordering_fields  = ['id', 'drug_name']


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset         = Prescription.objects.select_related(
                           'clinic', 'doctor', 'patient', 'appointment'
                       ).all().order_by('-prescription_date')
    serializer_class = PrescriptionSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['patient__first_name', 'doctor__first_name']
    ordering_fields  = ['id', 'prescription_date']


class PrescriptionLineViewSet(viewsets.ModelViewSet):
    queryset         = PrescriptionLine.objects.select_related(
                           'prescription', 'drug', 'disease'
                       ).all().order_by('id')
    serializer_class = PrescriptionLineSerializer
    pagination_class = StandardPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['drug__drug_name', 'disease__name']
    ordering_fields  = ['id', 'quantity']



@api_view(['GET'])
@cache_page(60 * 10)  # Cache for 10 minutes
def dropdown_options(request):
    """
    Returns all FK dropdown options for all models in one call.
    """
    clinics = list(Clinic.objects.values('id', 'clinic_name').order_by('clinic_name'))
    doctors = list(Doctor.objects.values('id', 'first_name', 'last_name').order_by('first_name'))
    patients = list(Patient.objects.values('id', 'first_name', 'last_name').order_by('first_name'))
    diseases = list(Disease.objects.filter(is_active=True).values('id', 'name').order_by('name'))
    appointments = list(Appointment.objects.values('id', 'op_number', 'appointment_datetime').order_by('-appointment_datetime')[:500])
    drugs = list(DrugMaster.objects.values('id', 'drug_name', 'generic_name').order_by('drug_name'))
    prescriptions = list(Prescription.objects.values('id', 'prescription_date', 'patient_id').order_by('-prescription_date')[:500])

    return Response({
        'clinics': [
            {'value': c['id'], 'label': c['clinic_name']}
            for c in clinics
        ],
        'doctors': [
            {'value': d['id'], 'label': f"{d['first_name']} {d['last_name'] or ''}".strip()}
            for d in doctors
        ],
        'patients': [
            {'value': p['id'], 'label': f"{p['first_name']} {p['last_name']}"}
            for p in patients
        ],
        'diseases': [
            {'value': d['id'], 'label': d['name']}
            for d in diseases
        ],
        'appointments': [
            {'value': a['id'], 'label': f"{a['op_number']} - {str(a['appointment_datetime'])[:10]}"}
            for a in appointments
        ],
        'drugs': [
            {'value': d['id'], 'label': f"{d['drug_name']} ({d['generic_name'] or 'generic'})"}
            for d in drugs
        ],
        'prescriptions': [
            {'value': p['id'], 'label': f"Prescription {p['id']} - {p['prescription_date']}"}
            for p in prescriptions
        ],
    })