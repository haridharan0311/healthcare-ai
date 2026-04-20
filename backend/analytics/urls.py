from django.urls import path
from . import views
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
    path('export/disease-trends/',     views.ExportDiseaseTrendsView.as_view(),   name='export-trends'),
    path('export/spike-alerts/',       views.ExportSpikeAlertsView.as_view(),     name='export-spikes'),
    path('export/restock/',            views.ExportRestockView.as_view(),          name='export-restock'),
    path('export/medicine-usage/',     views.ExportMedicineUsageView.as_view(),    name='export-medicine-usage'),
    path('export/doctor-trends/',      views.ExportDoctorTrendsView.as_view(),     name='export-doctor-trends'),
    path('export/reports/weekly/',     views.ExportWeeklyReportView.as_view(),     name='export-weekly'),
    path('export/reports/monthly/',    views.ExportMonthlyReportView.as_view(),    name='export-monthly'),
    path('export/low-stock-alerts/',   views.ExportLowStockAlertView.as_view(),    name='export-low-stock-alerts'),
    path('export/medicine-dependency/',views.ExportMedicineDependencyView.as_view(),name='export-medicine-dependency'),
    path('export/stock-depletion/',    views.ExportStockDepletionView.as_view(),   name='export-stock-depletion'),
    path('export-report/',             views.ExportReportView.as_view(),           name='export-report'),

    # ── UNIFIED SIMPLE FLOW API ───────────────────────────────────────
    path('insights/platform-dashboard/', insight_views.AnalyticsPlatformDashboardView.as_view(), name='platform-dashboard'),
    path('insights/summary/',            insight_views.InsightsSummaryView.as_view(),            name='insights-summary'),
    path('insights/alerts/',             insight_views.UnifiedAlertView.as_view(),               name='insights-alerts'),
    
    # ── DECOUPLED DASHBOARD (Progressive Loading) ─────────────────────
    path('dashboard/stats/',             views.dashboard_views.DashboardStatsView.as_view(),     name='dashboard-stats'),
    path('dashboard/trends/',            views.dashboard_views.DashboardTrendsView.as_view(),    name='dashboard-trends'),
    path('dashboard/medicines/',         views.dashboard_views.DashboardMedicinesView.as_view(), name='dashboard-medicines'),
    
    path('simulator/toggle/',            views.live_data_views.LiveDataToggleView.as_view(),    name='simulator-toggle'),

    path('simulator/toggle/',            views.live_data_views.LiveDataToggleView.as_view(),    name='simulator-toggle'),
]