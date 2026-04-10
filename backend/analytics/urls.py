from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from .views import crud_views
from .views.crud_views import dropdown_options
from .views import insight_views

urlpatterns = [
    # ── Core Analytics (Layer 1 + 2 + 3) ──────────────────────────────
    path('disease-trends/',            views.DiseaseTrendView.as_view(),      name='disease-trends'),
    path('disease-trends/timeseries/', views.TimeSeriesView.as_view(),        name='disease-timeseries'),
    path('medicine-usage/',            views.MedicineUsageView.as_view(),     name='medicine-usage'),

    # ── Spike Detection (both URL names per requirements doc) ──────────
    path('spike-alerts/',              views.SpikeAlertView.as_view(),        name='spike-alerts'),
    path('spike-detection/',           views.SpikeAlertView.as_view(),        name='spike-detection'),

    # ── Restock (system-wide + district) ──────────────────────────────
    path('restock-suggestions/',       views.RestockSuggestionView.as_view(), name='restock-suggestions'),
    path('district-restock/',          views.DistrictRestockView.as_view(),   name='district-restock'),

    # ── New Features ───────────────────────────────────────────────────
    path('trend-comparison/',          views.TrendComparisonView.as_view(),   name='trend-comparison'),
    path('top-medicines/',             views.TopMedicinesView.as_view(),      name='top-medicines'),
    path('low-stock-alerts/',          views.LowStockAlertView.as_view(),     name='low-stock-alerts'),
    path('seasonality/',               views.SeasonalityView.as_view(),       name='seasonality'),
    path('doctor-trends/',             views.DoctorWiseTrendsView.as_view(),  name='doctor-trends'),
    path('reports/weekly/',            views.WeeklyReportView.as_view(),      name='report-weekly'),
    path('reports/monthly/',           views.MonthlyReportView.as_view(),     name='report-monthly'),
    path('today-summary/', views.TodaySummaryView.as_view(), name='today-summary'),
    path('what-changed-today/', views.WhatChangedTodayView.as_view(), name='what-changed-today'),
    path('medicine-dependency/', views.MedicineDependencyView.as_view(), name='medicine-dependency'),
    path('stock-depletion/', views.StockDepletionForecastView.as_view(), name='stock-depletion'),
    path('adaptive-buffer/', views.AdaptiveBufferView.as_view(), name='adaptive-buffer'),

    # ── CSV Exports (all respect ?days= and ?district=) ────────────────
    path('export/disease-trends/',     views.ExportDiseaseTrendsView.as_view(),  name='export-trends'),
    path('export/spike-alerts/',       views.ExportSpikeAlertsView.as_view(),    name='export-spikes'),
    path('export/restock/',            views.ExportRestockView.as_view(),         name='export-restock'),
    path('export-report/',             views.ExportReportView.as_view(),          name='export-report'),

    # ── NEW: INSIGHT API (Layered Architecture) ────────────────────────
    # Analytics Engine Endpoints
    path('insights/health-dashboard/',         insight_views.HealthDashboardView.as_view(),           name='health-dashboard'),
    path('insights/disease-trends/analysis/',  insight_views.DiseaseTrendAnalysisView.as_view(),     name='disease-trends-analysis'),
    path('insights/medicine-usage/analysis/',  insight_views.MedicineUsageAnalysisView.as_view(),    name='medicine-usage-analysis'),

    # Prediction Engine Endpoints
    path('insights/predictions/disease-outbreaks/', insight_views.DiseaseOutbreakForecastView.as_view(), name='disease-outbreak-forecast'),
    path('insights/predictions/medicine-demand/',   insight_views.MedicineDemandForecastView.as_view(),   name='medicine-demand-forecast'),
    path('insights/predictions/resource-needs/',    insight_views.ResourceNeedsForecastView.as_view(),    name='resource-needs-forecast'),
    path('insights/predictions/dashboard/',         insight_views.ForecastDashboardView.as_view(),         name='forecast-dashboard'),

    # Decision Engine Endpoints
    path('insights/decisions/dashboard/',           insight_views.DecisionDashboardView.as_view(),           name='decision-dashboard'),
    path('insights/decisions/restock/',             insight_views.RestockDecisionsView.as_view(),             name='restock-decisions'),
    path('insights/decisions/outbreak-response/',   insight_views.OutbreakResponseDecisionsView.as_view(),   name='outbreak-response-decisions'),
    path('insights/decisions/resource-allocation/', insight_views.ResourceAllocationDecisionsView.as_view(), name='resource-allocation-decisions'),
    path('insights/decisions/risk-mitigation/',     insight_views.RiskMitigationDecisionsView.as_view(),     name='risk-mitigation-decisions'),

    # Feedback Engine Endpoints
    path('insights/feedback/prediction-accuracy/', insight_views.PredictionAccuracyView.as_view(), name='prediction-accuracy'),
    path('insights/feedback/decision-outcomes/',   insight_views.DecisionOutcomesView.as_view(),   name='decision-outcomes'),
    path('insights/feedback/improvement-recommendations/', insight_views.ImprovementRecommendationsView.as_view(), name='improvement-recommendations'),

    # Unified Platform Endpoint
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