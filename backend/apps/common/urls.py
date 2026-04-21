from django.urls import path

from apps.common.views import ActiveLegalDocumentListView, HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("legal-documents/", ActiveLegalDocumentListView.as_view(), name="legal-documents"),
]
