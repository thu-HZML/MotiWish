from rest_framework.routers import DefaultRouter

from apps.gacha.views import GachaPoolViewSet, GachaRecordViewSet

router = DefaultRouter()
router.register("pools", GachaPoolViewSet, basename="gacha-pool")
router.register("records", GachaRecordViewSet, basename="gacha-record")

urlpatterns = router.urls
