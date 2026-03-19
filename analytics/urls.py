from django.urls import path
from . import views

urlpatterns = [
    path('disease-trends/',            views.DiseaseTrendView.as_view(),      name='disease-trends'),
    path('disease-trends/timeseries/', views.TimeSeriesView.as_view(),        name='disease-timeseries'),
    path('spike-alerts/',              views.SpikeAlertView.as_view(),        name='spike-alerts'),
    path('restock-suggestions/',       views.RestockSuggestionView.as_view(), name='restock-suggestions'),
    path('export-report/',             views.ExportReportView.as_view(),      name='export-report'),
]