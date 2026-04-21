from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.shop.models import RedemptionRecord, WishItem
from apps.shop.serializers import RedemptionRecordSerializer, WishItemSerializer
from apps.shop.services import redeem_item


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="获取愿望商品列表",
        responses=api_envelope_serializer("WishItemListResponse", WishItemSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["Shop"],
        summary="创建愿望商品",
        request=WishItemSerializer,
        responses=api_envelope_serializer("WishItemCreateResponse", WishItemSerializer()),
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单个愿望商品",
        responses=api_envelope_serializer("WishItemDetailResponse", WishItemSerializer()),
    ),
    update=extend_schema(tags=["Shop"], summary="更新愿望商品", request=WishItemSerializer),
    partial_update=extend_schema(tags=["Shop"], summary="部分更新愿望商品", request=WishItemSerializer),
    destroy=extend_schema(tags=["Shop"], summary="删除愿望商品"),
)
class WishItemViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WishItemSerializer
    queryset = WishItem.objects.none()

    def get_queryset(self):
        return WishItem.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        tags=["Shop"],
        summary="兑换愿望商品",
        responses=api_envelope_serializer("WishItemRedeemResponse", RedemptionRecordSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="redeem")
    def redeem(self, request, pk=None):
        record = redeem_item(user=request.user, item=self.get_object())
        return api_response(data=RedemptionRecordSerializer(record).data, message="兑换成功")


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="获取兑换记录",
        responses=api_envelope_serializer("RedemptionRecordListResponse", RedemptionRecordSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单条兑换记录",
        responses=api_envelope_serializer("RedemptionRecordDetailResponse", RedemptionRecordSerializer()),
    ),
)
class RedemptionRecordViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RedemptionRecordSerializer
    queryset = RedemptionRecord.objects.none()

    def get_queryset(self):
        return RedemptionRecord.objects.filter(owner=self.request.user).select_related("item")
