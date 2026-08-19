from django.urls import path

from analytics.views import AnalyticsAPIView, dashboard_view

urlpatterns = [
    path("dashboard/", dashboard_view, name="dashboard"),
    path("analytics/", AnalyticsAPIView.as_view(), name="analytics-api"),
]
