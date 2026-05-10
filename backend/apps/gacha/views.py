from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.gacha.models import GachaDrawRecord, GachaPool, GachaPoolUserState
from apps.gacha.serializers import (
    GachaDrawRecordSerializer,
    GachaPoolSerializer,
    GachaPoolUserStateSerializer,
)
from apps.gacha.services import draw_once


@extend_schema_view(
    list=extend_schema(
        tags=["Gacha"],
        summary="获取卡池列表",
        description="返回当前可用卡池列表，包括四档奖励和三层保底参数。",
        responses=api_envelope_serializer("GachaPoolListResponse", GachaPoolSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["Gacha"],
        summary="获取单个卡池",
        description="返回指定卡池详情，包括奖励、概率与保底阈值。",
        responses=api_envelope_serializer("GachaPoolDetailResponse", GachaPoolSerializer()),
    ),
)
class GachaPoolViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GachaPoolSerializer
    queryset = GachaPool.objects.filter(is_active=True)

    @extend_schema(
        tags=["Gacha"],
        summary="查看当前卡池保底状态",
        description="返回当前用户在指定卡池上的抽卡累计与三层保底进度。",
        responses=api_envelope_serializer("GachaStateResponse", GachaPoolUserStateSerializer()),
    )
    @action(detail=True, methods=["get"], url_path="state")
    def state(self, request, pk=None):
        pool = self.get_object()
        state, _ = GachaPoolUserState.objects.get_or_create(owner=request.user, pool=pool)
        return api_response(data=GachaPoolUserStateSerializer(state).data, message="获取卡池状态成功")

    @extend_schema(
        tags=["Gacha"],
        summary="执行抽卡",
        description="执行单抽或多抽。服务端会在事务中统一处理一级货币扣费、二级货币发放、保底状态推进和抽卡记录生成。",
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
        description="返回当前用户的抽卡历史记录。",
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
