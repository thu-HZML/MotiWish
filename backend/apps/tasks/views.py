from datetime import date

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.tasks.models import Task, TaskOccurrence
from apps.tasks.serializers import TaskActionSerializer, TaskOccurrenceSerializer, TaskSerializer
from apps.tasks.services import complete_task, ensure_occurrences_for_date


class TaskViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        value = request.query_params.get("date")
        target_date = date.fromisoformat(value) if value else date.today()
        queryset = ensure_occurrences_for_date(request.user, target_date)
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取任务成功")

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        queryset = TaskOccurrence.objects.filter(owner=request.user).select_related("task")[:100]
        return api_response(data=TaskOccurrenceSerializer(queryset, many=True).data, message="获取历史记录成功")

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
