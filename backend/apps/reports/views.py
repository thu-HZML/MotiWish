from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, inline_serializer
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
