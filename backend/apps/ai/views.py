from rest_framework import status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.ai.agents.registry import agent_registry
from apps.ai.config import get_ai_provider_settings
from apps.ai.models import AIAgentRun, AIReportJob
from apps.ai.serializers import (
    AIAgentRunExecuteSerializer,
    AIAgentRunSerializer,
    AgentWorkflowDefinitionSerializer,
    AIProviderConfigSerializer,
    AIReportJobSerializer,
)
from apps.ai.services import create_agent_run, execute_agent_run
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
        summary="获取 Agent 运行记录列表",
        responses=api_envelope_serializer(
            "AIAgentRunListResponse", AIAgentRunSerializer(many=True)
        ),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建 Agent 运行记录",
        request=AIAgentRunSerializer,
        responses=api_envelope_serializer(
            "AIAgentRunCreateResponse", AIAgentRunSerializer()
        ),
    ),
    retrieve=extend_schema(
        tags=["AI"],
        summary="获取单个 Agent 运行记录",
        responses=api_envelope_serializer(
            "AIAgentRunDetailResponse", AIAgentRunSerializer()
        ),
    ),
)
class AIAgentRunViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AIAgentRunSerializer
    queryset = AIAgentRun.objects.none()
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return AIAgentRun.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent_run = create_agent_run(
            owner=request.user,
            workflow_key=serializer.validated_data["workflow_key"],
            input_payload=serializer.validated_data.get("input_payload", {}),
        )
        output = self.get_serializer(agent_run).data
        return api_response(
            data=output,
            message="创建 Agent 运行记录成功",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["AI"],
        summary="执行一次 mock Agent 工作流",
        request=AIAgentRunExecuteSerializer,
        responses=api_envelope_serializer(
            "AIAgentRunExecuteResponse", AIAgentRunSerializer()
        ),
    )
    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        agent_run = self.get_object()
        serializer = AIAgentRunExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("input_payload"):
            agent_run.input_payload = serializer.validated_data["input_payload"]
            agent_run.save(update_fields=["input_payload", "updated_at"])
        agent_run = execute_agent_run(agent_run=agent_run)
        return api_response(
            data=self.get_serializer(agent_run).data, message="执行 Agent 工作流成功"
        )
