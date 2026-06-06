from datetime import date

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.tasks.models import Task, TaskOccurrence
from apps.tasks.serializers import (
    TaskActionSerializer,
    TaskOccurrenceSerializer,
    TaskPricingPreviewPayloadSerializer,
    TaskPricingPreviewSerializer,
    TaskProgressUpdateSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
    build_preview_response,
)
from apps.tasks.services import complete_task, ensure_occurrences_for_date, sync_overdue_one_time_tasks, update_task_progress


@extend_schema_view(
    list=extend_schema(tags=["Tasks"], summary="获取任务列表", description="返回当前用户任务模板列表。", responses=api_envelope_serializer("TaskListResponse", TaskSerializer(many=True))),
    create=extend_schema(
        tags=["Tasks"],
        summary="创建任务",
        description="创建任务模板，支持常规轨道、探索轨道，以及 AI 定价会话。",
        request=TaskSerializer,
        responses=api_envelope_serializer("TaskCreateResponse", TaskSerializer()),
        examples=[
            OpenApiExample("创建常规轨道周期任务", value={"title": "Study 30 minutes", "description": "Daily study task", "task_type": "recurring", "recurrence": "daily", "settlement_track": "regular", "difficulty_level": "medium", "weekdays": [], "month_days": [], "metric_key": "study_minutes", "target_value": 30, "progress_target": 100, "starts_on": "2026-05-01", "status": "active", "tags": ["study", "english"]}, request_only=True),
            OpenApiExample("创建探索轨道任务", value={"title": "Debug training script", "description": "Find preprocessing issue", "task_type": "one_time", "recurrence": "none", "settlement_track": "exploration", "difficulty_level": "high", "estimated_focus_minutes": 180, "progress_target": 100, "due_at": "2026-05-12T23:00:00+08:00", "status": "active", "tags": ["research", "coding"]}, request_only=True),
        ],
    ),
    retrieve=extend_schema(tags=["Tasks"], summary="获取单个任务", responses=api_envelope_serializer("TaskRetrieveResponse", TaskSerializer())),
    update=extend_schema(tags=["Tasks"], summary="更新任务模板", request=TaskUpdateSerializer),
    partial_update=extend_schema(tags=["Tasks"], summary="部分更新任务模板", request=TaskUpdateSerializer),
    destroy=extend_schema(tags=["Tasks"], summary="删除任务"),
)
class TaskViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    queryset = Task.objects.none()

    def get_queryset(self):
        return Task.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return TaskUpdateSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        sync_overdue_one_time_tasks(user=request.user)
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Tasks"],
        summary="预览任务定价上下文",
        description="AI 定价会话创建前，后端归一化任务草稿，返回类型、结算轨道、难度估算、规模以及定价范围。",
        request=TaskPricingPreviewSerializer,
        responses=api_envelope_serializer("TaskPricingPreviewResponse", TaskPricingPreviewPayloadSerializer()),
        examples=[OpenApiExample("探索轨道任务定价预览", value={"title": "Debug training script", "task_type": "one_time", "recurrence": "none", "settlement_track": "exploration", "auto_estimate_difficulty": True, "estimated_focus_minutes": 180, "tags": ["debug", "research"]}, request_only=True)],
    )
    @action(detail=False, methods=["post"], url_path="pricing/preview")
    def pricing_preview(self, request):
        serializer = TaskPricingPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = build_preview_response(serializer.validated_data)
        return api_response(data=data, message="任务定价预览成功")

    @extend_schema(tags=["Tasks"], summary="获取日期任务实例", parameters=[OpenApiParameter(name="date", type=str, location=OpenApiParameter.QUERY, required=False, description="目标日期，格式 YYYY-MM-DD；默认今天。")], responses=api_envelope_serializer("TaskTodayResponse", TaskOccurrenceSerializer(many=True)))
    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        value = request.query_params.get("date")
        target_date = date.fromisoformat(value) if value else timezone.localdate()
        sync_overdue_one_time_tasks(user=request.user)
        queryset = ensure_occurrences_for_date(request.user, target_date)
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取任务成功")

    @extend_schema(tags=["Tasks"], summary="获取任务历史记录", description="返回当前用户任务实例历史记录。", responses=api_envelope_serializer("TaskHistoryResponse", TaskOccurrenceSerializer(many=True)))
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        sync_overdue_one_time_tasks(user=request.user)
        queryset = TaskOccurrence.objects.filter(owner=request.user).select_related("task")[:100]
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取历史记录成功")

    @extend_schema(tags=["Tasks"], summary="更新任务进度", description="更新任务实例进度，progress_target=目标值。", request=TaskProgressUpdateSerializer, responses=api_envelope_serializer("TaskProgressUpdateResponse", TaskOccurrenceSerializer()), examples=[OpenApiExample("更新今天任务进度", value={"progress": 60}, request_only=True), OpenApiExample("更新日期任务进度", value={"occurrence_date": "2026-06-03", "progress": 80}, request_only=True)])
    @action(detail=True, methods=["patch"], url_path="progress")
    def progress(self, request, pk=None):
        serializer = TaskProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        occurrence = update_task_progress(task=self.get_object(), progress=serializer.validated_data["progress"], target_date=serializer.validated_data.get("occurrence_date"))
        return api_response(data=TaskOccurrenceSerializer(occurrence).data, message="任务进度更新成功")

    @extend_schema(tags=["Tasks"], summary="完成结算任务", description="完成任务实例以及应用奖励/惩罚。周期任务 settle_period=true 返回周期完成率、漏做次数以及惩罚明细。", request=TaskActionSerializer, responses=api_envelope_serializer("TaskCompleteResponse", TaskOccurrenceSerializer()), examples=[OpenApiExample("完成今天任务", value={"progress": 100}, request_only=True), OpenApiExample("结算周期任务", value={"occurrence_date": "2026-06-04", "settle_period": True}, request_only=True)])
    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        occurrence = complete_task(task=self.get_object(), target_date=serializer.validated_data.get("occurrence_date"), progress=serializer.validated_data.get("progress"), settle_period=serializer.validated_data.get("settle_period", False))
        return api_response(data=TaskOccurrenceSerializer(occurrence).data, message="任务结算成功")
