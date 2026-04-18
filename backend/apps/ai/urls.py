from rest_framework.routers import DefaultRouter

from apps.ai.views import AIReportJobViewSet

router = DefaultRouter()
router.register("report-jobs", AIReportJobViewSet, basename="ai-report-job")

urlpatterns = router.urls
