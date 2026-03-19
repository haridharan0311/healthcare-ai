from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from . import crud_views
from .crud_views import dropdown_options

urlpatterns = [
    path('disease-trends/',            views.DiseaseTrendView.as_view(),      name='disease-trends'),
    path('disease-trends/timeseries/', views.TimeSeriesView.as_view(),        name='disease-timeseries'),
    path('spike-alerts/',              views.SpikeAlertView.as_view(),        name='spike-alerts'),
    path('restock-suggestions/',       views.RestockSuggestionView.as_view(), name='restock-suggestions'),
    path('export-report/',             views.ExportReportView.as_view(),      name='export-report'),
    path('crud/dropdowns/',            dropdown_options,                      name='dropdown-options'),
]

router = DefaultRouter()
router.register(r'crud/clinics',            crud_views.ClinicViewSet,           basename='clinic')
router.register(r'crud/doctors',            crud_views.DoctorViewSet,           basename='doctor')
router.register(r'crud/patients',           crud_views.PatientViewSet,          basename='patient')
router.register(r'crud/diseases',           crud_views.DiseaseViewSet,          basename='disease')
router.register(r'crud/appointments',       crud_views.AppointmentViewSet,      basename='appointment')
router.register(r'crud/drugs',              crud_views.DrugMasterViewSet,       basename='drug')
router.register(r'crud/prescriptions',      crud_views.PrescriptionViewSet,     basename='prescription')
router.register(r'crud/prescription-lines', crud_views.PrescriptionLineViewSet, basename='prescription-line')

urlpatterns += router.urls