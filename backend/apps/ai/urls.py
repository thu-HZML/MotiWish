from rest_framework.routers import DefaultRouter

from apps.ai.views import AIReportJobViewSet, AITaskPricingSessionViewSet

router = DefaultRouter()
router.register("report-jobs", AIReportJobViewSet, basename="ai-report-job")
router.register("task-pricing-sessions", AITaskPricingSessionViewSet, basename="ai-task-pricing-session")

urlpatterns = router.urls
