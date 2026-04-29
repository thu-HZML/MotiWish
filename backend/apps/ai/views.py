from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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
        description="返回当前用户创建的 AI 报告任务列表，适合 AI 页或历史报告页使用。",
        responses=api_envelope_serializer("AIReportJobListResponse", AIReportJobSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建 AI 报告任务",
        description="创建一条 AI 报告生成任务，用于后续异步分析、总结或推荐。",
        request=AIReportJobSerializer,
        responses=api_envelope_serializer("AIReportJobCreateResponse", AIReportJobSerializer()),
        examples=[
            OpenApiExample(
                "创建周报任务",
                value={
                    "report_type": "weekly",
                    "summary": "生成本周任务完成情况与建议",
                    "status": "pending",
                    "input_payload": {"range": "2026-W18"},
                    "result_payload": {},
                },
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["AI"],
        summary="获取单个 AI 报告任务",
        description="返回一条具体的 AI 报告任务详情，包括输入、状态和结果。",
        responses=api_envelope_serializer("AIReportJobDetailResponse", AIReportJobSerializer()),
    ),
    update=extend_schema(
        tags=["AI"],
        summary="更新 AI 报告任务",
        description="全量更新 AI 报告任务。",
        request=AIReportJobSerializer,
    ),
    partial_update=extend_schema(
        tags=["AI"],
        summary="部分更新 AI 报告任务",
        description="部分更新 AI 报告任务，例如回填状态或结果摘要。",
        request=AIReportJobSerializer,
    ),
    destroy=extend_schema(
        tags=["AI"],
        summary="删除 AI 报告任务",
        description="删除一条 AI 报告任务记录。",
    ),
)
class AIReportJobViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AIReportJobSerializer
    queryset = AIReportJob.objects.none()

    def get_queryset(self):
        return AIReportJob.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
