from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.shop.models import RedemptionRecord, UserInventory, WishItem
from apps.shop.serializers import (
    RedemptionActionSerializer,
    RedemptionRecordSerializer,
    ShopMetaSerializer,
    UserInventorySerializer,
    WishItemSerializer,
    WishPricingPreviewPayloadSerializer,
    WishPricingPreviewSerializer,
    build_shop_meta,
)
from apps.shop.services import (
    clamp_price_by_tier,
    fulfill_redemption,
    redeem_item,
    reject_redemption,
    use_inventory_item,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="获取商店商品列表",
        description="返回当前用户的商店商品，支持养成材料、功能轻道具和愿望奖励。",
        responses=api_envelope_serializer("ShopItemListResponse", WishItemSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["Shop"],
        summary="创建商店商品",
        description="创建可购买商品。养成材料需要配置 effect_payload.experience；功能轻道具会购买后进入库存。",
        request=WishItemSerializer,
        responses=api_envelope_serializer("ShopItemCreateResponse", WishItemSerializer()),
        examples=[
            OpenApiExample(
                "创建经验材料",
                value={
                    "title": "小份经验书",
                    "category": "growth_material",
                    "item_kind": "experience_pack",
                    "rarity": "common",
                    "price_tier": "small",
                    "price_secondary": 40,
                    "effect_payload": {"experience": 50},
                    "inventory": None,
                    "is_enabled": True,
                },
                request_only=True,
            ),
            OpenApiExample(
                "创建还债卡",
                value={
                    "title": "还债卡",
                    "category": "utility_item",
                    "item_kind": "debt_repayment_card",
                    "rarity": "rare",
                    "price_tier": "medium",
                    "price_secondary": 180,
                    "inventory": 10,
                    "is_enabled": True,
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单个商店商品",
        responses=api_envelope_serializer("ShopItemDetailResponse", WishItemSerializer()),
    ),
    update=extend_schema(tags=["Shop"], summary="更新商店商品", request=WishItemSerializer),
    partial_update=extend_schema(tags=["Shop"], summary="部分更新商店商品", request=WishItemSerializer),
    destroy=extend_schema(tags=["Shop"], summary="删除商店商品"),
)
class WishItemViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WishItemSerializer
    queryset = WishItem.objects.none()

    def get_queryset(self):
        queryset = WishItem.objects.filter(owner=self.request.user)
        category = self.request.query_params.get("category")
        item_kind = self.request.query_params.get("item_kind")
        if category:
            queryset = queryset.filter(category=category)
        if item_kind:
            queryset = queryset.filter(item_kind=item_kind)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        tags=["Shop"],
        summary="获取商店元信息",
        description="返回商品大类、商品类型、稀有度和价格档位，供前端渲染商店表单和筛选器。",
        responses=api_envelope_serializer("ShopMetaResponse", ShopMetaSerializer()),
    )
    @action(detail=False, methods=["get"], url_path="meta")
    def pricing_meta(self, request):
        return api_response(data=build_shop_meta(), message="获取商店元信息成功")

    @extend_schema(
        tags=["Shop"],
        summary="预览价格边界裁剪",
        description="根据价格档位返回裁剪后的合法价格。",
        request=WishPricingPreviewSerializer,
        responses=api_envelope_serializer("ShopPricingPreviewResponse", WishPricingPreviewPayloadSerializer()),
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
            "bounds": build_shop_meta()["bounds"][price_tier],
        }
        return api_response(data=data, message="价格预览成功")

    @extend_schema(
        tags=["Shop"],
        summary="购买商店商品",
        description="消耗二级货币购买商品。经验材料会直接增加用户经验；功能轻道具会进入库存；愿望奖励会生成待处理记录。",
        responses=api_envelope_serializer("ShopItemRedeemResponse", RedemptionRecordSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="redeem")
    def redeem(self, request, pk=None):
        record = redeem_item(user=request.user, item=self.get_object())
        return api_response(data=RedemptionRecordSerializer(record).data, message="购买成功")


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="获取库存列表",
        responses=api_envelope_serializer("InventoryListResponse", UserInventorySerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单个库存道具",
        responses=api_envelope_serializer("InventoryDetailResponse", UserInventorySerializer()),
    ),
)
class UserInventoryViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInventorySerializer
    pagination_class = None
    queryset = UserInventory.objects.none()

    def get_queryset(self):
        return UserInventory.objects.filter(owner=self.request.user, quantity__gt=0).select_related("item")

    @extend_schema(
        tags=["Shop"],
        summary="使用库存道具",
        description="当前支持主动使用还债卡，使用后会清空一级货币负债并扣除一张卡。",
        request=None,
        responses=api_envelope_serializer("InventoryUseResponse", UserInventorySerializer()),
    )
    @action(detail=True, methods=["post"], url_path="use")
    def use(self, request, pk=None):
        result = use_inventory_item(user=request.user, inventory=self.get_object())
        return api_response(data=UserInventorySerializer(result["inventory"]).data, message="道具使用成功")


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="获取兑换/购买记录",
        responses=api_envelope_serializer("RedemptionRecordListResponse", RedemptionRecordSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="获取单条兑换/购买记录",
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
        summary="兑现愿望奖励记录",
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
        summary="拒绝愿望奖励记录",
        request=RedemptionActionSerializer,
        responses=api_envelope_serializer("RedemptionRejectResponse", RedemptionRecordSerializer()),
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
