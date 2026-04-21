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
        responses=api_envelope_serializer("TaskListResponse", TaskSerializer(many=True)),
    ),
    create=extend_schema(
        tags=["Tasks"],
        summary="创建任务",
        request=TaskSerializer,
        responses=api_envelope_serializer("TaskCreateResponse", TaskSerializer()),
        examples=[
            OpenApiExample(
                "创建周期任务",
                value={
                    "title": "背单词 30 分钟",
                    "description": "每天晚饭后完成",
                    "task_type": "recurring",
                    "recurrence": "daily",
                    "weekdays": [],
                    "month_days": [],
                    "metric_key": "",
                    "target_value": None,
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
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Tasks"],
        summary="获取单个任务",
        responses=api_envelope_serializer("TaskRetrieveResponse", TaskSerializer()),
    ),
    update=extend_schema(tags=["Tasks"], summary="更新任务", request=TaskSerializer),
    partial_update=extend_schema(tags=["Tasks"], summary="部分更新任务", request=TaskSerializer),
    destroy=extend_schema(tags=["Tasks"], summary="删除任务"),
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
        summary="获取指定日期任务实例",
        parameters=[
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="日期，格式 YYYY-MM-DD；不传则默认为今天",
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
        summary="完成并结算任务",
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
