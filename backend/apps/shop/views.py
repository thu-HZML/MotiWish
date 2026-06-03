from django.db import models
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.shop.models import RedemptionRecord, UserInventory, WishItem
from apps.shop.serializers import (
    RedemptionActionSerializer,
    RedemptionRecordSerializer,
    WishItemSerializer,
    UserInventorySerializer,
)
from apps.shop.services import (
    ensure_default_shop_items,
    fulfill_redemption,
    redeem_item,
    use_inventory_item,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="获取商店商品列表",
        description="返回当前用户的商店商品，支持养成材料、功能轻道具和愿望奖励。",
        responses=api_envelope_serializer("ShopItemListResponse", WishItemSerializer(many=True)),
    ),
)
class WishItemViewSet(ApiResponseMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WishItemSerializer
    queryset = WishItem.objects.none()

    def get_queryset(self):
        ensure_default_shop_items()  # 触发创建全局公共默认商品
        # 返回系统公共商品 (owner is None) + 该用户创建的个性化愿望商品，且过滤掉下架商品
        queryset = WishItem.objects.filter(
            models.Q(owner=self.request.user) | models.Q(owner__isnull=True),
            is_enabled=True
        )
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset

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
# 已恢复：用户道具背包视图集
class UserInventoryViewSet(ApiResponseMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInventorySerializer
    queryset = UserInventory.objects.none()

    def get_queryset(self):
        return UserInventory.objects.filter(owner=self.request.user, quantity__gt=0).select_related("item")

    @extend_schema(
        tags=["Shop"],
        summary="使用库存道具",
        description="当前支持主动使用还债卡和放纵日卡。",
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
)
class RedemptionRecordViewSet(ApiResponseMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
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