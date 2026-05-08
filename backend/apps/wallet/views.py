from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.common.openapi import api_envelope_serializer
from apps.wallet.models import Wallet, WalletTransaction
from apps.wallet.serializers import WalletSerializer, WalletTransactionSerializer


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="获取钱包余额",
        description="返回当前用户钱包中的一级货币和二级货币余额。建议在首页、商城、抽卡页进入时调用。",
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
                        "primary_balance": 120,
                        "secondary_balance": 36,
                        "created_at": "2026-04-29T12:00:00+08:00",
                        "updated_at": "2026-04-29T12:00:00+08:00",
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
        description=(
            "返回当前用户最近的钱包变动记录，可按货币类型和变动原因筛选。"
            "适合用于资产明细页、任务结算回溯页、抽卡消耗记录页。"
        ),
        parameters=[
            OpenApiParameter(
                "currency_type",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description="货币类型筛选：primary=一级货币，secondary=二级货币。",
            ),
            OpenApiParameter(
                "reason",
                str,
                OpenApiParameter.QUERY,
                required=False,
                description=(
                    "交易原因筛选：task_reward、task_penalty、gacha_cost、"
                    "gacha_reward、shop_redeem、manual_adjust。"
                ),
            ),
        ],
        responses=api_envelope_serializer("WalletTransactionListResponse", WalletTransactionSerializer(many=True)),
        examples=[
            OpenApiExample(
                "一级货币奖励流水筛选",
                value=None,
                request_only=True,
                parameter_only=("currency_type", "reason"),
            ),
            OpenApiExample(
                "钱包流水响应片段",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "获取钱包流水成功",
                    "data": [
                        {
                            "id": 21,
                            "currency_type": "primary",
                            "reason": "task_reward",
                            "delta": 15,
                            "balance_before": 105,
                            "balance_after": 120,
                            "reference_type": "task_occurrence",
                            "reference_id": 88,
                            "memo": "完成任务：背单词 30 分钟",
                            "payload": {},
                            "created_at": "2026-04-29T11:15:00+08:00",
                        }
                    ],
                },
                response_only=True,
            ),
        ],
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
