import json
from collections.abc import Mapping

from django.core.serializers.json import DjangoJSONEncoder
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.ai.models import AIReportJob, AITaskPricingSession, AIWishPricingSession
from apps.ai.serializers import (
    AIReportJobSerializer,
    AITaskPricingFeedbackSerializer,
    AIWishDailyRefreshSerializer,
    AIWishPricingActionSerializer,
    AIWishPricingSessionCreateSerializer,
    AIWishPricingSessionSerializer,
    AITaskPricingSessionCreateSerializer,
    AITaskPricingSessionSerializer,
)
from apps.ai.services import (
    accept_task_pricing_session,
    accept_wish_pricing_session,
    cancel_wish_pricing_session,
    create_task_pricing_session,
    create_wish_pricing_session,
    generate_daily_wish_refresh,
    revise_task_pricing_session,
)
from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.common.timezones import format_business_datetime


USER_SUPPLIED_TASK_TIME_FIELDS = ("starts_on", "ends_on", "due_at")


def _task_payload_preserving_user_time_fields(*, validated_payload, raw_payload):
    payload = json.loads(json.dumps(validated_payload, cls=DjangoJSONEncoder))
    if not isinstance(raw_payload, Mapping):
        return payload

    for field in USER_SUPPLIED_TASK_TIME_FIELDS:
        if field in raw_payload and raw_payload[field] not in (None, ""):
            payload[field] = raw_payload[field]
    if payload.get("due_at"):
        payload["due_at"] = format_business_datetime(payload["due_at"]) or payload["due_at"]
    return payload


@extend_schema_view(
    list=extend_schema(
        tags=["AI"],
        summary="获取 AI 报告任务列表",
        responses=AIReportJobSerializer(many=True),
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


@extend_schema_view(
    list=extend_schema(
        tags=["AI"],
        summary="获取任务定价会话列表",
        responses=AITaskPricingSessionSerializer(many=True),
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
        task_payload = _task_payload_preserving_user_time_fields(
            validated_payload=serializer.validated_data["task_payload"],
            raw_payload=request.data.get("task_payload"),
        )
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


@extend_schema_view(
    list=extend_schema(
        tags=["AI"],
        summary="获取愿望定价/刷新候选列表",
        responses=api_envelope_serializer("AIWishPricingSessionListResponse", AIWishPricingSessionSerializer(many=True)),
    ),
    retrieve=extend_schema(
        tags=["AI"],
        summary="获取愿望定价/刷新候选详情",
        responses=api_envelope_serializer("AIWishPricingSessionDetailResponse", AIWishPricingSessionSerializer()),
    ),
    create=extend_schema(
        tags=["AI"],
        summary="创建手动愿望定价会话",
        description=(
            "前端提交用户自定义愿望草稿后，AI 会先判断 small / medium / large 档位，"
            "再结合用户画像、近期任务和历史愿望给出精确定价。该接口只创建待确认会话，"
            "需要调用 confirm 接口后才会创建真正的商店商品。"
        ),
        request=AIWishPricingSessionCreateSerializer,
        responses=api_envelope_serializer("AIWishPricingSessionCreateResponse", AIWishPricingSessionSerializer()),
        examples=[
            OpenApiExample(
                "手动愿望定价",
                value={
                    "wish_payload": {
                        "title": "周末去吃一顿喜欢的餐厅",
                        "description": "完成本周计划后作为奖励。",
                        "tags": ["food", "rest"],
                    }
                },
                request_only=True,
            )
        ],
    ),
)
class AIWishPricingSessionViewSet(ApiResponseMixin, viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = AIWishPricingSessionSerializer
    queryset = AIWishPricingSession.objects.none()
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return AIWishPricingSession.objects.filter(owner=self.request.user).select_related("generated_item")

    def create(self, request, *args, **kwargs):
        serializer = AIWishPricingSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = create_wish_pricing_session(
            user=request.user,
            wish_payload=serializer.validated_data["wish_payload"],
            source=AIWishPricingSession.Source.MANUAL,
        )
        return api_response(data=self.get_serializer(session).data, message="愿望定价会话已创建")

    @extend_schema(
        tags=["AI"],
        summary="每日刷新愿望候选",
        description=(
            "后端每日固定时间可调用同一逻辑生成一个待确认愿望候选。"
            "该候选结合用户画像、近期任务、历史愿望，并在提示词中允许轻微折扣以增强正反馈。"
            "同一用户同一天默认只生成一次；force=true 可强制重刷。"
        ),
        request=AIWishDailyRefreshSerializer,
        responses=api_envelope_serializer("AIWishDailyRefreshResponse", AIWishPricingSessionSerializer()),
    )
    @action(detail=False, methods=["post"], url_path="daily-refresh")
    def daily_refresh(self, request):
        serializer = AIWishDailyRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session, created = generate_daily_wish_refresh(
            user=request.user,
            refresh_date=serializer.validated_data.get("refresh_date"),
            force=serializer.validated_data.get("force", False),
        )
        message = "每日愿望候选已生成" if created else "今日已有愿望候选"
        return api_response(data=self.get_serializer(session).data, message=message)

    @extend_schema(
        tags=["AI"],
        summary="确认或取消愿望候选",
        description="accept 会创建真正的用户私有愿望商品；cancel 只取消当前候选。",
        request=AIWishPricingActionSerializer,
        responses=api_envelope_serializer("AIWishPricingActionResponse", AIWishPricingSessionSerializer()),
        examples=[
            OpenApiExample("确认创建商品", value={"action": "accept"}, request_only=True),
            OpenApiExample("取消候选", value={"action": "cancel"}, request_only=True),
        ],
    )
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        serializer = AIWishPricingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = self.get_object()
        if serializer.validated_data["action"] == "accept":
            session = accept_wish_pricing_session(session=session)
            return api_response(data=self.get_serializer(session).data, message="愿望商品已创建")
        session = cancel_wish_pricing_session(session=session)
        return api_response(data=self.get_serializer(session).data, message="愿望候选已取消")
