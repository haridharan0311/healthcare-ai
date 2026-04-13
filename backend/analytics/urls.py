from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from .views import crud_views
from .views.crud_views import dropdown_options
from .views import insight_views

urlpatterns = [
    # ── Core Analytics ────────────────────────────────────────────────
    path('disease-trends/',            views.DiseaseTrendView.as_view(),      name='disease-trends'),
    path('disease-trends/timeseries/', views.TimeSeriesView.as_view(),        name='disease-timeseries'),
    path('medicine-usage/',            views.MedicineUsageView.as_view(),     name='medicine-usage'),

    # ── Spike Detection ───────────────────────────────────────────────
    path('spike-alerts/',              views.SpikeAlertView.as_view(),        name='spike-alerts'),
    path('spike-detection/',           views.SpikeAlertView.as_view(),        name='spike-detection'),

    # ── Restock ───────────────────────────────────────────────────────
    path('restock-suggestions/',       views.RestockSuggestionView.as_view(), name='restock-suggestions'),
    path('district-restock/',          views.DistrictRestockView.as_view(),   name='district-restock'),

    # ── Features ──────────────────────────────────────────────────────
    path('trend-comparison/',          views.TrendComparisonView.as_view(),   name='trend-comparison'),
    path('top-medicines/',             views.TopMedicinesView.as_view(),      name='top-medicines'),
    path('low-stock-alerts/',          views.LowStockAlertView.as_view(),     name='low-stock-alerts'),
    path('seasonality/',               views.SeasonalityView.as_view(),       name='seasonality'),
    path('doctor-trends/',             views.DoctorWiseTrendsView.as_view(),  name='doctor-trends'),
    path('reports/weekly/',            views.WeeklyReportView.as_view(),      name='report-weekly'),
    path('reports/monthly/',           views.MonthlyReportView.as_view(),     name='report-monthly'),
    path('today-summary/',             views.TodaySummaryView.as_view(),      name='today-summary'),
    path('what-changed-today/',        views.WhatChangedTodayView.as_view(),  name='what-changed-today'),
    path('medicine-dependency/',       views.MedicineDependencyView.as_view(), name='medicine-dependency'),
    path('stock-depletion/',           views.StockDepletionForecastView.as_view(), name='stock-depletion'),
    path('adaptive-buffer/',           views.AdaptiveBufferView.as_view(),    name='adaptive-buffer'),

    # ── CSV Exports ───────────────────────────────────────────────────
    path('export/disease-trends/',     views.ExportDiseaseTrendsView.as_view(),  name='export-trends'),
    path('export/spike-alerts/',       views.ExportSpikeAlertsView.as_view(),    name='export-spikes'),
    path('export/restock/',            views.ExportRestockView.as_view(),         name='export-restock'),
    path('export-report/',             views.ExportReportView.as_view(),          name='export-report'),

    # ── UNIFIED SIMPLE FLOW API ───────────────────────────────────────
    path('insights/platform-dashboard/', insight_views.AnalyticsPlatformDashboardView.as_view(), name='platform-dashboard'),

    # ── CRUD ───────────────────────────────────────────────────────────
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