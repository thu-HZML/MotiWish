from datetime import date

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.common.openapi import api_envelope_serializer
from apps.tasks.models import Task, TaskOccurrence
from apps.tasks.serializers import TaskActionSerializer, TaskOccurrenceSerializer, TaskSerializer
from apps.tasks.services import complete_task, ensure_occurrences_for_date


@extend_schema_view(
    list=extend_schema(
        tags=["Tasks"],
        summary="获取任务列表",
        description="返回当前登录用户创建的任务模板列表。这里返回的是任务定义，不是按日期展开后的任务实例。",
        responses=api_envelope_serializer("TaskListResponse", TaskSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["Tasks"],
        summary="创建任务",
        description=(
            "创建一个任务模板。"
            "task_type 用于区分日常、周期和一次性任务；recurrence 用于描述周期规则。"
        ),
        request=TaskSerializer,
        responses=api_envelope_serializer("TaskCreateResponse", TaskSerializer()),
        examples=[
            OpenApiExample(
                "创建每日学习任务",
                value={
                    "title": "背单词 30 分钟",
                    "description": "每天晚饭后完成",
                    "task_type": "recurring",
                    "recurrence": "daily",
                    "weekdays": [],
                    "month_days": [],
                    "metric_key": "study_minutes",
                    "target_value": 30,
                    "progress_target": 100,
                    "reward_primary": 15,
                    "penalty_primary": 3,
                    "starts_on": "2026-04-21",
                    "ends_on": None,
                    "due_at": None,
                    "status": "active",
                    "tags": ["study", "english"],
                    "ai_metadata": {"source": "manual"},
                },
                request_only=True,
            ),
            OpenApiExample(
                "创建每周健身任务",
                value={
                    "title": "去健身房训练",
                    "description": "固定在周一、周三、周六执行",
                    "task_type": "recurring",
                    "recurrence": "weekly",
                    "weekdays": [0, 2, 5],
                    "month_days": [],
                    "metric_key": "",
                    "target_value": None,
                    "progress_target": 100,
                    "reward_primary": 20,
                    "penalty_primary": 5,
                    "starts_on": "2026-05-01",
                    "ends_on": None,
                    "due_at": None,
                    "status": "active",
                    "tags": ["health", "sport"],
                    "ai_metadata": {"source": "manual"},
                },
                request_only=True,
            ),
            OpenApiExample(
                "创建一次性截止任务",
                value={
                    "title": "提交课程大作业",
                    "description": "在截止日前上传最终版本",
                    "task_type": "one_time",
                    "recurrence": "none",
                    "weekdays": [],
                    "month_days": [],
                    "metric_key": "",
                    "target_value": None,
                    "progress_target": 100,
                    "reward_primary": 50,
                    "penalty_primary": 0,
                    "starts_on": "2026-05-01",
                    "ends_on": "2026-05-15",
                    "due_at": "2026-05-15T23:59:00+08:00",
                    "status": "active",
                    "tags": ["school", "deadline"],
                    "ai_metadata": {"source": "manual"},
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Tasks"],
        summary="获取单个任务",
        description="返回指定任务模板的完整字段。",
        responses=api_envelope_serializer("TaskRetrieveResponse", TaskSerializer()),
    ),
    update=extend_schema(
        tags=["Tasks"],
        summary="更新任务",
        description="全量更新任务模板。未提供的字段会被重置，因此更适合结构性修改。",
        request=TaskSerializer,
    ),
    partial_update=extend_schema(
        tags=["Tasks"],
        summary="部分更新任务",
        description="部分更新任务模板，适合只修改奖励、时间、标签等少数字段。",
        request=TaskSerializer,
    ),
    destroy=extend_schema(
        tags=["Tasks"],
        summary="删除任务",
        description="删除任务模板及其关联的任务实例记录。",
    ),
)
class TaskViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    queryset = Task.objects.none()

    def get_queryset(self):
        return Task.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        tags=["Tasks"],
        summary="获取指定日期的任务实例",
        description=(
            "根据给定日期生成并返回当天应出现的任务实例。"
            "这里返回的是 TaskOccurrence，包含任务模板和当天的完成状态。"
        ),
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
        description="返回当前用户最近 100 条任务实例记录，可用于历史页、统计页或结算回溯。",
        responses=api_envelope_serializer("TaskHistoryResponse", TaskOccurrenceSerializer(many=True)),
    )
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        queryset = TaskOccurrence.objects.filter(owner=request.user).select_related("task")[:100]
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取历史记录成功")

    @extend_schema(
        tags=["Tasks"],
        summary="完成并结算任务",
        description=(
            "将指定任务在某一天的实例标记为 completed，并按 reward_primary 发放一级货币奖励。"
            "如果不传 progress，则自动使用任务的 progress_target。"
        ),
        request=TaskActionSerializer,
        responses=api_envelope_serializer("TaskCompleteResponse", TaskOccurrenceSerializer()),
        examples=[
            OpenApiExample(
                "任务结算请求",
                value={"occurrence_date": "2026-04-21", "progress": 100},
                request_only=True,
            )
        ],
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
