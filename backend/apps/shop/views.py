from django.db import models
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.shop.catalog import DEFAULT_SHOP_ITEMS
from apps.shop.models import RedemptionRecord, ShopItemCategory, UserInventory, WishItem
from apps.shop.serializers import (
    CustomWishItemSerializer,
    RedemptionActionSerializer,
    RedemptionRecordSerializer,
    UserInventorySerializer,
    WishItemSerializer,
)
from apps.shop.services import ensure_default_shop_items, fulfill_redemption, redeem_item, use_inventory_item


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="\u83b7\u53d6\u5546\u5e97\u5546\u54c1\u5217\u8868",
        description="\u8fd4\u56de\u5f53\u524d\u7528\u6237\u53ef\u89c1\u7684\u5546\u5e97\u5546\u54c1\uff0c\u5305\u62ec\u516c\u5171\u5546\u54c1\u548c\u7528\u6237\u81ea\u5efa\u613f\u671b\u5546\u54c1\u3002",
        responses=api_envelope_serializer("ShopItemListResponse", WishItemSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["Shop"],
        summary="\u521b\u5efa\u81ea\u5efa\u613f\u671b\u5546\u54c1",
        description="\u7528\u6237\u81ea\u5b9a\u4e49\u613f\u671b\u5546\u54c1\uff0c\u4f8b\u5982\u65c5\u6e38\u5956\u52b1\u3001\u5916\u98df\u5956\u52b1\u7b49\u3002\u81ea\u5efa\u5546\u54c1\u53ea\u5c5e\u4e8e\u5f53\u524d\u7528\u6237\uff0c\u5e76\u53ea\u4f1a\u51fa\u73b0\u5728\u81ea\u5df1\u7684\u5546\u54c1\u5217\u8868\u4e2d\u3002",
        request=CustomWishItemSerializer,
        responses=api_envelope_serializer("CustomWishItemCreateResponse", CustomWishItemSerializer()),
        examples=[
            OpenApiExample(
                "\u521b\u5efa\u65c5\u6e38\u5956\u52b1",
                value={
                    "title": "Travel reward",
                    "description": "A self-defined trip reward.",
                    "price_tier": "large",
                    "price_secondary": 800,
                    "rarity": "epic",
                    "inventory": 1,
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(tags=["Shop"], summary="\u66f4\u65b0\u81ea\u5efa\u613f\u671b\u5546\u54c1", request=CustomWishItemSerializer),
    partial_update=extend_schema(tags=["Shop"], summary="\u90e8\u5206\u66f4\u65b0\u81ea\u5efa\u613f\u671b\u5546\u54c1", request=CustomWishItemSerializer),
    destroy=extend_schema(tags=["Shop"], summary="\u5220\u9664\u81ea\u5efa\u613f\u671b\u5546\u54c1"),
)
class WishItemViewSet(
    ApiResponseMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = WishItemSerializer
    queryset = WishItem.objects.none()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return CustomWishItemSerializer
        return WishItemSerializer

    def get_queryset(self):
        ensure_default_shop_items()

        if self.action in {"update", "partial_update", "destroy"}:
            return WishItem.objects.filter(owner=self.request.user, category=ShopItemCategory.WISH)

        queryset = WishItem.objects.filter(
            models.Q(owner=self.request.user) | models.Q(owner__isnull=True),
            is_enabled=True,
        )
        default_catalog_keys = [item["catalog_key"] for item in DEFAULT_SHOP_ITEMS]
        queryset = queryset.exclude(owner=self.request.user, catalog_key__in=default_catalog_keys)

        category = self.request.query_params.get("category")
        item_kind = self.request.query_params.get("item_kind")

        if category:
            if category == "growth_material":
                queryset = queryset.filter(category=ShopItemCategory.EXPERIENCE_PACK)
            elif category == "utility_item":
                queryset = queryset.filter(
                    category__in=[
                        ShopItemCategory.DEBT_REPAYMENT_CARD,
                        ShopItemCategory.TASK_FAILURE_PROTECTION_CARD,
                        ShopItemCategory.INDULGENCE_DAY_CARD,
                    ]
                )
            elif category == "wish_reward":
                queryset = queryset.filter(category=ShopItemCategory.WISH)
            else:
                queryset = queryset.filter(category=category)

        if item_kind:
            queryset = queryset.filter(category=item_kind)

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user,
            category=ShopItemCategory.WISH,
            catalog_key="",
            is_enabled=True,
            is_stackable=True,
            effect_payload={"source": "user_custom_wish"},
        )

    def perform_update(self, serializer):
        serializer.save(category=ShopItemCategory.WISH, catalog_key="")

    @extend_schema(
        tags=["Shop"],
        summary="\u8d2d\u4e70\u5546\u5e97\u5546\u54c1",
        description="\u6d88\u8017\u4e8c\u7ea7\u8d27\u5e01\u8d2d\u4e70\u5546\u54c1\u3002\u613f\u671b\u5546\u54c1\u4f1a\u751f\u6210\u5f85\u5904\u7406\u7684\u5151\u6362\u8bb0\u5f55\u3002",
        responses=api_envelope_serializer("ShopItemRedeemResponse", RedemptionRecordSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="redeem")
    def redeem(self, request, pk=None):
        record = redeem_item(user=request.user, item=self.get_object())
        return api_response(data=RedemptionRecordSerializer(record).data, message="\u8d2d\u4e70\u6210\u529f")


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="\u83b7\u53d6\u5e93\u5b58\u5217\u8868",
        responses=api_envelope_serializer("InventoryListResponse", UserInventorySerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Shop"],
        summary="\u83b7\u53d6\u5355\u4e2a\u5e93\u5b58\u9053\u5177",
        responses=api_envelope_serializer("InventoryDetailResponse", UserInventorySerializer()),
    ),
)
class UserInventoryViewSet(ApiResponseMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInventorySerializer
    queryset = UserInventory.objects.none()

    def get_queryset(self):
        return UserInventory.objects.filter(owner=self.request.user, quantity__gt=0).select_related("item")

    @extend_schema(
        tags=["Shop"],
        summary="\u4f7f\u7528\u5e93\u5b58\u9053\u5177",
        description="\u5f53\u524d\u652f\u6301\u4e3b\u52a8\u4f7f\u7528\u8fd8\u503a\u5361\u548c\u653e\u7eb5\u65e5\u5361\u3002",
        responses=api_envelope_serializer("InventoryUseResponse", UserInventorySerializer()),
    )
    @action(detail=True, methods=["post"], url_path="use")
    def use(self, request, pk=None):
        result = use_inventory_item(user=request.user, inventory=self.get_object())
        return api_response(data=UserInventorySerializer(result["inventory"]).data, message="\u9053\u5177\u4f7f\u7528\u6210\u529f")


@extend_schema_view(
    list=extend_schema(
        tags=["Shop"],
        summary="\u83b7\u53d6\u5151\u6362/\u8d2d\u4e70\u8bb0\u5f55",
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
        summary="\u5151\u73b0\u613f\u671b\u5956\u52b1\u8bb0\u5f55",
        request=RedemptionActionSerializer,
        responses=api_envelope_serializer("RedemptionFulfillResponse", RedemptionRecordSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="fulfill")
    def fulfill(self, request, pk=None):
        serializer = RedemptionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = fulfill_redemption(record=self.get_object(), note=serializer.validated_data.get("note", ""))
        return api_response(data=RedemptionRecordSerializer(record).data, message="\u5151\u6362\u5df2\u5151\u73b0")
