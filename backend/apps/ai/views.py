import json

from django.core.serializers.json import DjangoJSONEncoder
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.ai.models import AIReportJob, AITaskPricingSession
from apps.ai.serializers import (
    AIReportJobSerializer,
    AITaskPricingFeedbackSerializer,
    AITaskPricingSessionCreateSerializer,
    AITaskPricingSessionSerializer,
)
from apps.ai.services import accept_task_pricing_session, create_task_pricing_session, revise_task_pricing_session
from apps.common.api import ApiResponseMixin, api_response
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
        responses=api_envelope_serializer("AITaskPricingSessionListResponse", AITaskPricingSessionSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["AI"],
        summary="获取任务定价会话详情",
        responses=api_envelope_serializer("AITaskPricingSessionDetailResponse", AITaskPricingSessionSerializer()),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建任务定价会话",
        description=(
            "前端提交任务草稿后，后端会读取用户画像和全局任务定价标准，"
            "返回 quote_payload。前端展示报价后，再调用 feedback 接口让用户接受或反馈。"
        ),
        request=AITaskPricingSessionCreateSerializer,
        responses=api_envelope_serializer("AITaskPricingSessionCreateResponse", AITaskPricingSessionSerializer()),
        examples=[
            OpenApiExample(
                "一次性任务",
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
            ),
            OpenApiExample(
                "日常任务",
                value={
                    "task_payload": {
                        "title": "英语听力 30 分钟",
                        "task_type": "daily",
                        "recurrence": "daily",
                        "settlement_track": "regular",
                        "difficulty_level": "medium",
                        "metric_key": "study_minutes",
                        "target_value": 30,
                        "progress_target": 100,
                        "tags": ["english"],
                    }
                },
                request_only=True,
            ),
            OpenApiExample(
                "每周周期任务",
                value={
                    "task_payload": {
                        "title": "每周健身 3 次",
                        "task_type": "recurring",
                        "recurrence": "weekly",
                        "settlement_track": "regular",
                        "difficulty_level": "medium",
                        "weekdays": [1, 3, 5],
                        "progress_target": 100,
                        "tags": ["fitness"],
                    }
                },
                request_only=True,
            ),
            OpenApiExample(
                "探索任务",
                value={
                    "task_payload": {
                        "title": "排查训练脚本问题",
                        "task_type": "one_time",
                        "recurrence": "none",
                        "settlement_track": "exploration",
                        "difficulty_level": "high",
                        "estimated_focus_minutes": 180,
                        "progress_target": 100,
                        "tags": ["coding", "research"],
                    }
                },
                request_only=True,
            ),
        ],
    ),
)
class AITaskPricingSessionViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AITaskPricingSessionSerializer
    queryset = AITaskPricingSession.objects.none()
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return AITaskPricingSession.objects.filter(owner=self.request.user).select_related("created_task")

    def create(self, request, *args, **kwargs):
        serializer = AITaskPricingSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_payload = json.loads(json.dumps(serializer.validated_data["task_payload"], cls=DjangoJSONEncoder))
        session = create_task_pricing_session(user=request.user, task_payload=task_payload)
        return api_response(data=self.get_serializer(session).data, message="任务定价会话已创建")

    @extend_schema(
        tags=["AI"],
        summary="反馈或接受任务定价",
        description=(
            "action=revise 时根据偏高/偏低/详细说明重新定价；"
            "action=accept 时接受当前 quote_payload，创建正式任务，并更新用户动态画像。"
        ),
        request=AITaskPricingFeedbackSerializer,
        responses=api_envelope_serializer("AITaskPricingFeedbackResponse", AITaskPricingSessionSerializer()),
        examples=[
            OpenApiExample("接受当前定价", value={"action": "accept"}, request_only=True),
            OpenApiExample(
                "认为定价偏低",
                value={
                    "action": "revise",
                    "feedback_direction": "too_low",
                    "feedback_text": "这个任务需要额外查资料，奖励可以再高一点。",
                },
                request_only=True,
            ),
            OpenApiExample(
                "详细反馈",
                value={
                    "action": "revise",
                    "feedback_direction": "detail",
                    "feedback_text": "惩罚偏重，我最近压力比较大，希望失败成本轻一些。",
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="feedback")
    def feedback(self, request, pk=None):
        serializer = AITaskPricingFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = self.get_object()
        if serializer.validated_data["action"] == "accept":
            session = accept_task_pricing_session(session=session)
            return api_response(data=self.get_serializer(session).data, message="任务定价已接受，任务已创建")

        session = revise_task_pricing_session(
            session=session,
            feedback_direction=serializer.validated_data.get("feedback_direction", ""),
            feedback_text=serializer.validated_data.get("feedback_text", ""),
        )
        return api_response(data=self.get_serializer(session).data, message="任务定价已根据反馈调整")
