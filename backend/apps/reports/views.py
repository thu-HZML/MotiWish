from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.tasks.models import OccurrenceStatus, TaskOccurrence
from apps.wallet.models import Wallet


class DashboardReportView(APIView):
    permission_classes = [IsAuthenticated]

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
