from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.common.openapi import api_envelope_serializer
from apps.tasks.models import OccurrenceStatus, TaskOccurrence
from apps.wallet.models import Wallet


class DashboardReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Reports"],
        summary="获取仪表盘报表",
        description=(
            "返回首页仪表盘所需的轻量统计数据，包括钱包余额和任务完成概览。"
            "适合首页、个人中心首页卡片使用。"
        ),
        responses=api_envelope_serializer(
            "DashboardReportResponse",
            inline_serializer(
                name="DashboardReportPayload",
                fields={
                    "wallet": inline_serializer(
                        name="DashboardWalletData",
                        fields={
                            "primary_balance": serializers.IntegerField(),
                            "secondary_balance": serializers.IntegerField(),
                        },
                    ),
                    "task_stats": inline_serializer(
                        name="DashboardTaskStats",
                        fields={
                            "total": serializers.IntegerField(),
                            "completed": serializers.IntegerField(),
                        },
                    ),
                },
            ),
        ),
        examples=[
            OpenApiExample(
                "仪表盘报表示例",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "获取报表成功",
                    "data": {
                        "wallet": {"primary_balance": 120, "secondary_balance": 36},
                        "task_stats": {"total": 58, "completed": 41},
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(owner=request.user)
        task_stats = TaskOccurrence.objects.filter(owner=request.user).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=OccurrenceStatus.COMPLETED)),
        )
        return api_response(
            data={
                "wallet": {
                    "primary_balance": wallet.primary_balance,
                    "secondary_balance": wallet.secondary_balance,
                },
                "task_stats": task_stats,
            },
            message="获取报表成功",
        )
