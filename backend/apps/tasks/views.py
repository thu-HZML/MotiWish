from datetime import date

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.tasks.models import DifficultyLevel, SettlementTrack, Task, TaskOccurrence, TaskType
from apps.tasks.serializers import (
    TaskActionSerializer,
    TaskOccurrenceSerializer,
    TaskPricingApplySerializer,
    TaskPricingMetaSerializer,
    TaskPricingPreviewPayloadSerializer,
    TaskPricingPreviewSerializer,
    TaskProgressUpdateSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
    build_preview_response,
)
from apps.tasks.services import (
    apply_task_pricing,
    complete_task,
    ensure_occurrences_for_date,
    request_task_pricing,
    update_task_progress,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Tasks"],
        summary="获取任务列表",
        description="返回当前登录用户创建的任务模板列表。",
        responses=TaskSerializer(many=True),
    ),
    create=extend_schema(
        tags=["Tasks"],
        summary="创建任务",
        description="创建一个任务模板。现在支持常规轨道和探索轨道两种定价模式。",
        request=TaskSerializer,
        responses=api_envelope_serializer("TaskCreateResponse", TaskSerializer()),
        examples=[
            OpenApiExample(
                "创建常规轨道周期任务",
                value={
                    "title": "背单词 30 分钟",
                    "description": "每天晚饭后完成",
                    "task_type": "recurring",
                    "recurrence": "daily",
                    "settlement_track": "regular",
                    "difficulty_level": "medium",
                    "weekdays": [],
                    "month_days": [],
                    "metric_key": "study_minutes",
                    "target_value": 30,
                    "progress_target": 100,
                    "starts_on": "2026-05-01",
                    "status": "active",
                    "tags": ["study", "english"],
                },
                request_only=True,
            ),
            OpenApiExample(
                "创建探索轨道任务",
                value={
                    "title": "排查训练脚本中的隐藏 Bug",
                    "description": "目标是定位数据预处理阶段的异常",
                    "task_type": "one_time",
                    "recurrence": "none",
                    "settlement_track": "exploration",
                    "difficulty_level": "high",
                    "estimated_focus_minutes": 180,
                    "progress_target": 100,
                    "due_at": "2026-05-12T23:00:00+08:00",
                    "status": "active",
                    "tags": ["research", "coding"],
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Tasks"],
        summary="获取单个任务",
        responses=api_envelope_serializer("TaskRetrieveResponse", TaskSerializer()),
    ),
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

    @extend_schema(
        tags=["Tasks"],
        summary="获取任务定价元信息",
        description="返回前端构建任务定价表单和 AI 定价提示所需的模式、公式和难度系数提示。",
        responses=api_envelope_serializer("TaskPricingMetaResponse", TaskPricingMetaSerializer()),
    )
    @action(detail=False, methods=["get"], url_path="pricing/meta")
    def pricing_meta(self, request):
        data = {
            "settlement_tracks": [
                {"value": SettlementTrack.REGULAR, "label": "常规轨道"},
                {"value": SettlementTrack.EXPLORATION, "label": "探索轨道"},
            ],
            "formulas": {
                TaskType.ONE_TIME: "Reward = round_5(R * F_progress(p) * F_time)",
                TaskType.RECURRING: "RecurringReward = round_5(B * F_cycle(r) * S)",
                TaskType.DAILY: "RecurringReward = round_5(B * F_cycle(r) * S)",
                SettlementTrack.EXPLORATION: "ExplorationReward = round_5(T_focus * K_difficulty)",
            },
            "difficulty_factors": {
                DifficultyLevel.LOW: 15,
                DifficultyLevel.MEDIUM: 25,
                DifficultyLevel.HIGH: 40,
            },
        }
        return api_response(data=data, message="获取任务定价元信息成功")

    @extend_schema(
        tags=["Tasks"],
        summary="预览任务定价请求载荷",
        description="在真正调用 AI 定价前，先让后端对任务输入做模式归一化，返回将交给 AI 的标准化上下文。",
        request=TaskPricingPreviewSerializer,
        responses=api_envelope_serializer("TaskPricingPreviewResponse", TaskPricingPreviewPayloadSerializer()),
        examples=[
            OpenApiExample(
                "探索轨道预览",
                value={
                    "task_type": "one_time",
                    "recurrence": "none",
                    "settlement_track": "exploration",
                    "difficulty_level": "high",
                    "estimated_focus_minutes": 180,
                    "tags": ["research", "coding"],
                },
                request_only=True,
            )
        ],
    )
    @action(detail=False, methods=["post"], url_path="pricing/preview")
    def pricing_preview(self, request):
        serializer = TaskPricingPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = build_preview_response(serializer.validated_data)
        return api_response(data=data, message="任务定价预览成功")

    @extend_schema(
        tags=["Tasks"],
        summary="发起任务 AI 定价请求",
        description="将任务标记为待 AI 定价，并固化当前定价上下文快照。当前接口只负责框架和状态流转，不执行真实 AI。",
        responses=api_envelope_serializer("TaskPricingRequestResponse", TaskSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="pricing/request")
    def pricing_request(self, request, pk=None):
        task = request_task_pricing(task=self.get_object())
        return api_response(
            data=TaskSerializer(task, context={"request": request}).data,
            message="任务定价请求已创建",
        )

    @extend_schema(
        tags=["Tasks"],
        summary="应用任务定价结果",
        description="供后续 AI 回调或人工测试使用：把 reward_primary / penalty_primary 和 AI 定价结果写回任务。",
        request=TaskPricingApplySerializer,
        responses=api_envelope_serializer("TaskPricingApplyResponse", TaskSerializer()),
        examples=[
            OpenApiExample(
                "应用 AI 定价结果",
                value={
                    "reward_primary": 120,
                    "penalty_primary": 25,
                    "pricing_payload": {
                        "model": "gpt-5.5",
                        "reasoning": "该任务为高难度探索任务，预计专注 180 分钟。",
                        "confidence": 0.84,
                    },
                },
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="pricing/apply")
    def pricing_apply(self, request, pk=None):
        serializer = TaskPricingApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = apply_task_pricing(
            task=self.get_object(),
            reward_primary=serializer.validated_data["reward_primary"],
            penalty_primary=serializer.validated_data["penalty_primary"],
            pricing_payload=serializer.validated_data.get("pricing_payload", {}),
        )
        return api_response(
            data=TaskSerializer(task, context={"request": request}).data,
            message="任务定价结果已应用",
        )

    @extend_schema(
        tags=["Tasks"],
        summary="获取指定日期的任务实例",
        parameters=[
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="目标日期，格式 YYYY-MM-DD；不传则默认今天。",
            )
        ],
        responses=api_envelope_serializer("TaskTodayResponse", TaskOccurrenceSerializer(many=True)),
    )
    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        value = request.query_params.get("date")
        target_date = date.fromisoformat(value) if value else date.today()
        queryset = ensure_occurrences_for_date(request.user, target_date)
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取任务成功")

    @extend_schema(
        tags=["Tasks"],
        summary="获取任务历史记录",
        responses=api_envelope_serializer("TaskHistoryResponse", TaskOccurrenceSerializer(many=True)),
    )
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        queryset = TaskOccurrence.objects.filter(owner=request.user).select_related("task")[:100]
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取历史记录成功")

    @extend_schema(
        tags=["Tasks"],
        summary="更新任务实际进度",
        description=(
            "更新指定日期任务实例的实际完成进度；不传 occurrence_date 时默认更新今天。"
            "任务模板中的 progress_target 是目标值，不用于记录实际进度。"
        ),
        request=TaskProgressUpdateSerializer,
        responses=api_envelope_serializer("TaskProgressUpdateResponse", TaskOccurrenceSerializer()),
        examples=[
            OpenApiExample(
                "更新今天的任务进度",
                value={"progress": 60},
                request_only=True,
            ),
            OpenApiExample(
                "更新指定日期的任务进度",
                value={"occurrence_date": "2026-06-03", "progress": 80},
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["patch"], url_path="progress")
    def progress(self, request, pk=None):
        serializer = TaskProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        occurrence = update_task_progress(
            task=self.get_object(),
            progress=serializer.validated_data["progress"],
            target_date=serializer.validated_data.get("occurrence_date"),
        )
        return api_response(
            data=TaskOccurrenceSerializer(occurrence).data,
            message="任务进度已更新",
        )

    @extend_schema(
        tags=["Tasks"],
        summary="完成并结算任务",
        request=TaskActionSerializer,
        responses=api_envelope_serializer("TaskCompleteResponse", TaskOccurrenceSerializer()),
    )
    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        occurrence = complete_task(
            task=self.get_object(),
            target_date=serializer.validated_data.get("occurrence_date"),
            progress=serializer.validated_data.get("progress"),
        )
        return api_response(data=TaskOccurrenceSerializer(occurrence).data, message="任务结算成功")
