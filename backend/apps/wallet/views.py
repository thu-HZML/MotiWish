from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.common.openapi import api_envelope_serializer
from apps.wallet.models import Wallet, WalletTransaction
from apps.wallet.serializers import WalletSerializer, WalletTransactionSerializer
from apps.wallet.services import reset_primary_debt


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="获取钱包余额",
        description="返回当前用户钱包余额，同时包含一级货币负债状态和负债下限信息。",
        responses=api_envelope_serializer("WalletDetailResponse", WalletSerializer()),
        examples=[
            OpenApiExample(
                "钱包余额响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "获取钱包成功",
                    "data": {
                        "id": 1,
                        "primary_balance": -35,
                        "secondary_balance": 120,
                        "primary_debt": 35,
                        "is_in_debt": True,
                        "primary_debt_floor": -100,
                        "created_at": "2026-05-08T10:00:00+08:00",
                        "updated_at": "2026-05-08T10:00:00+08:00",
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(owner=request.user)
        return api_response(data=WalletSerializer(wallet).data, message="获取钱包成功")


class WalletTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="获取钱包流水",
        description="返回最近的钱包变动记录，可按货币类型和原因筛选。",
        parameters=[
            OpenApiParameter(
                "currency_type",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description="货币类型筛选：primary 或 secondary。",
            ),
            OpenApiParameter(
                "reason",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description=(
                    "交易原因筛选：task_reward、task_penalty、gacha_cost、gacha_reward、"
                    "shop_redeem、manual_adjust、debt_reset。"
                ),
            ),
        ],
        responses=api_envelope_serializer("WalletTransactionListResponse", WalletTransactionSerializer(many=True)),
    )
    def get(self, request):
        queryset = WalletTransaction.objects.filter(owner=self.request.user)
        currency_type = request.query_params.get("currency_type")
        reason = request.query_params.get("reason")
        if currency_type:
            queryset = queryset.filter(currency_type=currency_type)
        if reason:
            queryset = queryset.filter(reason=reason)
        data = WalletTransactionSerializer(queryset[:100], many=True).data
        return api_response(data=data, message="获取钱包流水成功")


class WalletDebtResetView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="执行一级货币债务重置",
        description="将当前一级货币负债清零。若当前没有负债，则返回当前钱包状态且不产生流水。",
        request=None,
        responses=api_envelope_serializer("WalletDebtResetResponse", WalletSerializer()),
        examples=[
            OpenApiExample(
                "债务重置响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "债务重置完成",
                    "data": {
                        "id": 1,
                        "primary_balance": 0,
                        "secondary_balance": 120,
                        "primary_debt": 0,
                        "is_in_debt": False,
                        "primary_debt_floor": -100,
                    },
                },
                response_only=True,
            )
        ],
    )
    def post(self, request):
        wallet, _ = reset_primary_debt(user=request.user)
        return api_response(data=WalletSerializer(wallet).data, message="债务重置完成")
