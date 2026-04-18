from django.urls import path

from apps.reports.views import DashboardReportView

urlpatterns = [
    path("dashboard/", DashboardReportView.as_view(), name="dashboard-report"),
]
