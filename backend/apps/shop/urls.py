from rest_framework.routers import DefaultRouter

from apps.shop.views import RedemptionRecordViewSet, WishItemViewSet

router = DefaultRouter()
router.register("items", WishItemViewSet, basename="wish-item")
router.register("redemptions", RedemptionRecordViewSet, basename="redemption-record")

urlpatterns = router.urls
