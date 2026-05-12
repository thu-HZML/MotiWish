from rest_framework import status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.ai.models import AIReportJob, AITaskPricingSession
from apps.ai.serializers import (
    AIReportJobSerializer,
    AITaskPricingFeedbackSerializer,
    AITaskPricingSessionCreateSerializer,
    AITaskPricingSessionSerializer,
)
from apps.ai.services import (
    accept_task_pricing_session,
    create_task_pricing_session,
    revise_task_pricing_session,
)
from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer


class AgentWorkflowCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI"],
        summary="获取 AI 工作流目录",
        responses=api_envelope_serializer(
            "AgentWorkflowCatalogResponse",
            AgentWorkflowDefinitionSerializer(many=True),
        ),
    )
    def get(self, request):
        return api_response(
            data=AgentWorkflowDefinitionSerializer(
                agent_registry.list_workflows(), many=True
            ).data,
            message="获取 AI 工作流目录成功",
        )


class AIProviderConfigView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI"],
        summary="获取当前 AI 模型提供商配置",
        responses=api_envelope_serializer(
            "AIProviderConfigResponse",
            AIProviderConfigSerializer(),
        ),
    )
    def get(self, request):
        return api_response(
            data=AIProviderConfigSerializer(get_ai_provider_settings().__dict__).data,
            message="获取 AI Provider 配置成功",
        )


@extend_schema_view(
    list=extend_schema(
        tags=["AI"],
        summary="获取 AI 报告任务列表",
        description="返回当前用户创建的 AI 报告任务列表，适合 AI 页或历史报告页使用。",
        responses=api_envelope_serializer(
            "AIReportJobListResponse", AIReportJobSerializer(many=True)
        ),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建 AI 报告任务",
        description="创建一条 AI 报告生成任务，用于后续异步分析、总结或推荐。",
        request=AIReportJobSerializer,
        responses=api_envelope_serializer(
            "AIReportJobCreateResponse", AIReportJobSerializer()
        ),
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
        responses=api_envelope_serializer(
            "AIReportJobDetailResponse", AIReportJobSerializer()
        ),
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


@extend_schema_view(
    list=extend_schema(
        tags=["AI"],
        summary="获取任务定价会话列表",
        responses=api_envelope_serializer(
            "AITaskPricingSessionListResponse",
            AITaskPricingSessionSerializer(many=True),
        ),
    ),
    retrieve=extend_schema(
        tags=["AI"],
        summary="获取任务定价会话详情",
        responses=api_envelope_serializer(
            "AITaskPricingSessionDetailResponse", AITaskPricingSessionSerializer()
        ),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建任务定价会话",
        description="提交任务草稿，AI 读取用户画像和全局任务定价标准后生成初步定价，等待前端反馈。",
        request=AITaskPricingSessionCreateSerializer,
        responses=api_envelope_serializer(
            "AITaskPricingSessionCreateResponse", AITaskPricingSessionSerializer()
        ),
        examples=[
            OpenApiExample(
                "创建一次性任务定价会话",
                value={
                    "task_payload": {
                        "title": "完成数据库课程复习",
                        "description": "整理索引、事务、范式相关笔记",
                        "task_type": "one_time",
                        "recurrence": "none",
                        "settlement_track": "regular",
                        "difficulty_level": "medium",
                        "progress_target": 100,
                        "tags": ["study", "database"],
                    }
                },
                request_only=True,
            )
        ],
    ),
)
class AITaskPricingSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AITaskPricingSessionSerializer
    queryset = AITaskPricingSession.objects.none()
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return AITaskPricingSession.objects.filter(
            owner=self.request.user
        ).select_related("created_task")

    def create(self, request, *args, **kwargs):
        serializer = AITaskPricingSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = create_task_pricing_session(
            user=request.user,
            task_payload=serializer.validated_data["task_payload"],
        )
        return api_response(
            data=self.get_serializer(session).data, message="任务定价会话已创建"
        )

    @extend_schema(
        tags=["AI"],
        summary="反馈或接受任务定价",
        description="action=revise 时根据偏高/偏低/详细说明重新定价；action=accept 时创建正式任务并更新用户动态画像。",
        request=AITaskPricingFeedbackSerializer,
        responses=api_envelope_serializer(
            "AITaskPricingFeedbackResponse", AITaskPricingSessionSerializer()
        ),
    )
    @action(detail=True, methods=["post"], url_path="feedback")
    def feedback(self, request, pk=None):
        serializer = AITaskPricingFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = self.get_object()
        if serializer.validated_data["action"] == "accept":
            session = accept_task_pricing_session(session=session)
            return api_response(
                data=self.get_serializer(session).data,
                message="任务定价已接受，任务已创建",
            )

        session = revise_task_pricing_session(
            session=session,
            feedback_direction=serializer.validated_data.get("feedback_direction", ""),
            feedback_text=serializer.validated_data.get("feedback_text", ""),
        )
        return api_response(
            data=self.get_serializer(session).data, message="任务定价已根据反馈调整"
        )
