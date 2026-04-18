from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.shop.models import RedemptionRecord, WishItem
from apps.shop.serializers import RedemptionRecordSerializer, WishItemSerializer
from apps.shop.services import redeem_item


class WishItemViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WishItemSerializer

    def get_queryset(self):
        return WishItem.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], url_path="redeem")
    def redeem(self, request, pk=None):
        record = redeem_item(user=request.user, item=self.get_object())
        return api_response(data=RedemptionRecordSerializer(record).data, message="兑换成功")


class RedemptionRecordViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RedemptionRecordSerializer

    def get_queryset(self):
        return RedemptionRecord.objects.filter(owner=self.request.user).select_related("item")
