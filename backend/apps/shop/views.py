from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.shop.models import RedemptionRecord, WishItem, WishPriceTier
from apps.shop.serializers import (
    RedemptionActionSerializer,
    RedemptionRecordSerializer,
    WishItemSerializer,
    WishPricingMetaSerializer,
    WishPricingPreviewPayloadSerializer,
    WishPricingPreviewSerializer,
)
from apps.shop.services import PRICE_BOUNDS, clamp_price_by_tier, fulfill_redemption, redeem_item, reject_redemption


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
        description="创建一个可兑换的愿望商品。价格需要符合当前档位的边界约束。",
        request=WishItemSerializer,
        responses=api_envelope_serializer("WishItemCreateResponse", WishItemSerializer()),
        examples=[
            OpenApiExample(
                "创建中愿望商品",
                value={
                    "title": "周末看一场电影",
                    "description": "完成阶段目标后的放松奖励",
                    "source": "manual",
                    "price_tier": "medium",
                    "price_secondary": 180,
                    "inventory": 1,
                    "is_enabled": True,
                    "auto_refund_on_reject": True,
                    "ai_pricing": {"source": "manual"},
                },
                request_only=True,
            )
        ],
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
        summary="获取愿望定价元信息",
        description="返回前端构建愿望定价表单和 AI 定价边界所需的价格档位信息。",
        responses=api_envelope_serializer("WishPricingMetaResponse", WishPricingMetaSerializer()),
    )
    @action(detail=False, methods=["get"], url_path="pricing/meta")
    def pricing_meta(self, request):
        data = {
            "tiers": [
                {"value": WishPriceTier.SMALL, "label": "小愿望"},
                {"value": WishPriceTier.MEDIUM, "label": "中愿望"},
                {"value": WishPriceTier.LARGE, "label": "大愿望"},
            ],
            "bounds": PRICE_BOUNDS,
        }
        return api_response(data=data, message="获取愿望定价元信息成功")

    @extend_schema(
        tags=["Shop"],
        summary="预览愿望定价边界裁剪",
        description="在真正应用 AI 定价前，先让后端根据价格档位返回裁剪后的合法价格。",
        request=WishPricingPreviewSerializer,
        responses=api_envelope_serializer("WishPricingPreviewResponse", WishPricingPreviewPayloadSerializer()),
        examples=[
            OpenApiExample(
                "大愿望价格预览",
                value={"price_tier": "large", "suggested_price": 1600},
                request_only=True,
            )
        ],
    )
    @action(detail=False, methods=["post"], url_path="pricing/preview")
    def pricing_preview(self, request):
        serializer = WishPricingPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        price_tier = serializer.validated_data["price_tier"]
        suggested_price = serializer.validated_data["suggested_price"]
        data = {
            "price_tier": price_tier,
            "requested_price": suggested_price,
            "clamped_price": clamp_price_by_tier(price_tier=price_tier, suggested_price=suggested_price),
            "bounds": PRICE_BOUNDS[price_tier],
        }
        return api_response(data=data, message="愿望定价预览成功")

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
        description="返回当前用户的兑换历史。",
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

    @extend_schema(
        tags=["Shop"],
        summary="兑现兑换记录",
        description="将待处理兑换记录标记为已兑现。",
        request=RedemptionActionSerializer,
        responses=api_envelope_serializer("RedemptionFulfillResponse", RedemptionRecordSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="fulfill")
    def fulfill(self, request, pk=None):
        serializer = RedemptionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = fulfill_redemption(record=self.get_object(), note=serializer.validated_data.get("note", ""))
        return api_response(data=RedemptionRecordSerializer(record).data, message="兑换已兑现")

    @extend_schema(
        tags=["Shop"],
        summary="拒绝兑换记录",
        description="将待处理兑换记录标记为已拒绝。默认根据商品设置自动退款。",
        request=RedemptionActionSerializer,
        responses=api_envelope_serializer("RedemptionRejectResponse", RedemptionRecordSerializer()),
        examples=[
            OpenApiExample(
                "拒绝并自动退款",
                value={"note": "当前不满足兑现条件", "refund": True},
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        serializer = RedemptionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = reject_redemption(
            record=self.get_object(),
            note=serializer.validated_data.get("note", ""),
            refund=serializer.validated_data.get("refund"),
        )
        return api_response(data=RedemptionRecordSerializer(record).data, message="兑换已拒绝")
