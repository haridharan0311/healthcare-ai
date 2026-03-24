from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from . import crud_views
from .crud_views import dropdown_options

urlpatterns = [
    # ── Analytics APIs ─────────────────────────────────────────────────
    # 1.1 Disease Aggregation
    path('disease-trends/',            views.DiseaseTrendView.as_view(),      name='disease-trends'),
    # 1.2 Time-Series Aggregation
    path('disease-trends/timeseries/', views.TimeSeriesView.as_view(),        name='disease-timeseries'),
    # 1.3 Medicine Usage Aggregation
    path('medicine-usage/',            views.MedicineUsageView.as_view(),     name='medicine-usage'),
    # 2.3 Spike Detection (both route names as per document)
    path('spike-alerts/',              views.SpikeAlertView.as_view(),        name='spike-alerts'),
    path('spike-detection/',           views.SpikeAlertView.as_view(),        name='spike-detection'),
    # 2.4 + 2.5 Demand + Restock
    path('restock-suggestions/',       views.RestockSuggestionView.as_view(), name='restock-suggestions'),
    # District-level restock
    path('district-restock/',          views.DistrictRestockView.as_view(),   name='district-restock'),
    # ── Export APIs ────────────────────────────────────────────────────
    path('export/disease-trends/',     views.ExportDiseaseTrendsView.as_view(), name='export-trends'),
    path('export/spike-alerts/',       views.ExportSpikeAlertsView.as_view(),   name='export-spikes'),
    path('export/restock/',            views.ExportRestockView.as_view(),        name='export-restock'),
    path('export-report/',             views.ExportReportView.as_view(),         name='export-report'),
    # ── CRUD dropdown ─────────────────────────────────────────────────
    path('crud/dropdowns/',            dropdown_options,                       name='dropdown-options'),
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