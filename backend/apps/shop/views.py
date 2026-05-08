from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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
        description="返回当前用户创建的愿望商品列表，适合商城首页、愿望管理页使用。",
        responses=api_envelope_serializer("WishItemListResponse", WishItemSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["Shop"],
        summary="创建愿望商品",
        description="创建一个可兑换的愿望商品或奖励项。",
        request=WishItemSerializer,
        responses=api_envelope_serializer("WishItemCreateResponse", WishItemSerializer()),
        examples=[
            OpenApiExample(
                "创建愿望商品",
                value={
                    "title": "周末看一场电影",
                    "description": "完成阶段目标后的放松奖励",
                    "source": "manual",
                    "cost_secondary": 120,
                    "inventory": 1,
                    "is_enabled": True,
                    "ai_pricing": {"source": "manual"},
                },
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单个愿望商品",
        description="返回一条愿望商品的详细配置。",
        responses=api_envelope_serializer("WishItemDetailResponse", WishItemSerializer()),
    ),
    update=extend_schema(
        tags=["Shop"],
        summary="更新愿望商品",
        description="全量更新愿望商品配置。",
        request=WishItemSerializer,
    ),
    partial_update=extend_schema(
        tags=["Shop"],
        summary="部分更新愿望商品",
        description="部分更新愿望商品，例如调整库存、价格或上下架状态。",
        request=WishItemSerializer,
    ),
    destroy=extend_schema(
        tags=["Shop"],
        summary="删除愿望商品",
        description="删除愿望商品及其后续可见性。",
    ),
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
        description="消耗二级货币兑换指定愿望商品，并生成兑换记录。",
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
        description="返回当前用户的兑换历史，可用于商城历史页和奖励兑现跟踪页。",
        responses=api_envelope_serializer("RedemptionRecordListResponse", RedemptionRecordSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单条兑换记录",
        description="返回一条具体的兑换记录明细。",
        responses=api_envelope_serializer("RedemptionRecordDetailResponse", RedemptionRecordSerializer()),
    ),
)
class RedemptionRecordViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RedemptionRecordSerializer
    queryset = RedemptionRecord.objects.none()

    def get_queryset(self):
        return RedemptionRecord.objects.filter(owner=self.request.user).select_related("item")
