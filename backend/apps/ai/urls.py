from rest_framework.routers import DefaultRouter

from apps.ai.views import AIReportJobViewSet, AITaskPricingSessionViewSet

router = DefaultRouter()
router.register("report-jobs", AIReportJobViewSet, basename="ai-report-job")
router.register(
    "task-pricing-sessions",
    AITaskPricingSessionViewSet,
    basename="ai-task-pricing-session",
)

urlpatterns = [
    path(
        "workflows/catalog/",
        AgentWorkflowCatalogView.as_view(),
        name="ai-workflow-catalog",
    ),
    path(
        "providers/current/", AIProviderConfigView.as_view(), name="ai-provider-config"
    ),
]

urlpatterns += router.urls
