from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.ai.models import AIReportJob
from apps.ai.serializers import AIReportJobSerializer
from apps.common.api import ApiResponseMixin
from apps.common.openapi import api_envelope_serializer


@extend_schema_view(
    list=extend_schema(
        tags=["AI"],
        summary="获取 AI 报告任务列表",
        responses=api_envelope_serializer("AIReportJobListResponse", AIReportJobSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建 AI 报告任务",
        request=AIReportJobSerializer,
        responses=api_envelope_serializer("AIReportJobCreateResponse", AIReportJobSerializer()),
    ),
    retrieve=extend_schema(
        tags=["AI"],
        summary="获取单个 AI 报告任务",
        responses=api_envelope_serializer("AIReportJobDetailResponse", AIReportJobSerializer()),
    ),
    update=extend_schema(tags=["AI"], summary="更新 AI 报告任务", request=AIReportJobSerializer),
    partial_update=extend_schema(tags=["AI"], summary="部分更新 AI 报告任务", request=AIReportJobSerializer),
    destroy=extend_schema(tags=["AI"], summary="删除 AI 报告任务"),
)
class AIReportJobViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AIReportJobSerializer
    queryset = AIReportJob.objects.none()

    def get_queryset(self):
        return AIReportJob.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
