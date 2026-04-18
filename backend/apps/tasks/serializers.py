from rest_framework import serializers

from apps.tasks.models import Task, TaskOccurrence


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "task_type",
            "recurrence",
            "weekdays",
            "month_days",
            "metric_key",
            "target_value",
            "progress_target",
            "reward_primary",
            "penalty_primary",
            "starts_on",
            "ends_on",
            "due_at",
            "status",
            "tags",
            "ai_metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class TaskOccurrenceSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)

    class Meta:
        model = TaskOccurrence
        fields = (
            "id",
            "task",
            "occurrence_date",
            "status",
            "progress",
            "settled_at",
            "reward_transaction_id",
            "penalty_transaction_id",
            "created_at",
            "updated_at",
        )


class TaskActionSerializer(serializers.Serializer):
    occurrence_date = serializers.DateField(required=False)
    progress = serializers.IntegerField(required=False, min_value=0)
