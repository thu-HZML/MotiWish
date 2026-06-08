from rest_framework.routers import DefaultRouter

from apps.ai.views import AIReportJobViewSet, AITaskPricingSessionViewSet, AIWishPricingSessionViewSet

router = DefaultRouter()
router.register("report-jobs", AIReportJobViewSet, basename="ai-report-job")
router.register("task-pricing-sessions", AITaskPricingSessionViewSet, basename="ai-task-pricing-session")
router.register("wish-pricing-sessions", AIWishPricingSessionViewSet, basename="ai-wish-pricing-session")

urlpatterns = router.urls
