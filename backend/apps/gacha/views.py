from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.gacha.models import GachaDrawRecord, GachaPool
from apps.gacha.serializers import GachaDrawRecordSerializer, GachaPoolSerializer
from apps.gacha.services import draw_once


@extend_schema_view(
    list=extend_schema(
        tags=["Gacha"],
        summary="获取卡池列表",
        description="返回当前可用的抽卡池列表。前端通常在抽卡首页进入时调用。",
        responses=api_envelope_serializer("GachaPoolListResponse", GachaPoolSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Gacha"],
        summary="获取单个卡池",
        description="返回指定卡池的完整配置，包括消耗、概率和保底参数。",
        responses=api_envelope_serializer("GachaPoolDetailResponse", GachaPoolSerializer()),
    ),
)
class GachaPoolViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GachaPoolSerializer
    queryset = GachaPool.objects.filter(is_active=True)

    @extend_schema(
        tags=["Gacha"],
        summary="执行抽卡",
        description=(
            "执行单抽或多抽。当前支持一次请求抽 1 到 10 次，"
            "后端会在事务中统一处理扣费、发奖和记录生成。"
        ),
        responses=api_envelope_serializer("GachaDrawResponse", GachaDrawRecordSerializer(many=True)),
        examples=[
            OpenApiExample("单抽请求", value={"times": 1}, request_only=True),
            OpenApiExample("十连请求", value={"times": 10}, request_only=True),
        ],
    )
    @action(detail=True, methods=["post"], url_path="draw")
    def draw(self, request, pk=None):
        times = int(request.data.get("times", 1))
        pool = self.get_object()

        if times < 1 or times > 10:
            return api_response(code=400, message="抽卡次数不合法，仅支持 1-10 次。", status_code=400)

        records = []
        try:
            with transaction.atomic():
                for _ in range(times):
                    record = draw_once(user=request.user, pool=pool)
                    records.append(record)
        except Exception as exc:
            return api_response(code=400, message=str(exc), status_code=400)

        return api_response(
            data=GachaDrawRecordSerializer(records, many=True).data,
            message=f"成功抽卡 {times} 次",
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Gacha"],
        summary="获取抽卡记录",
        description="返回当前用户的抽卡历史记录，适合抽卡记录页和资产回顾页使用。",
        responses=api_envelope_serializer("GachaRecordListResponse", GachaDrawRecordSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Gacha"],
        summary="获取单条抽卡记录",
        description="返回一条具体的抽卡结果记录。",
        responses=api_envelope_serializer("GachaRecordDetailResponse", GachaDrawRecordSerializer()),
    ),
)
class GachaRecordViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GachaDrawRecordSerializer
    queryset = GachaDrawRecord.objects.none()

    def get_queryset(self):
        return GachaDrawRecord.objects.filter(owner=self.request.user).select_related("pool")
