from rest_framework.routers import DefaultRouter

from django.urls import path

from apps.ai.views import AIAgentRunViewSet, AIProviderConfigView, AgentWorkflowCatalogView, AIReportJobViewSet

router = DefaultRouter()
router.register("report-jobs", AIReportJobViewSet, basename="ai-report-job")
router.register("agent-runs", AIAgentRunViewSet, basename="ai-agent-run")

urlpatterns = [
    path("workflows/catalog/", AgentWorkflowCatalogView.as_view(), name="ai-workflow-catalog"),
    path("providers/current/", AIProviderConfigView.as_view(), name="ai-provider-config"),
]

urlpatterns += router.urls
