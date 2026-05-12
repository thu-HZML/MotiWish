from rest_framework import serializers

from apps.ai.models import AIReportJob, AITaskPricingSession
from apps.tasks.serializers import TaskSerializer


class AIReportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReportJob
        fields = "__all__"
        read_only_fields = ("owner", "status", "summary", "result_payload")


class AITaskPricingSessionSerializer(serializers.ModelSerializer):
    created_task = TaskSerializer(read_only=True)

    class Meta:
        model = AITaskPricingSession
        fields = "__all__"
        read_only_fields = (
            "owner",
            "status",
            "profile_snapshot",
            "pricing_standard_version",
            "pricing_standard_excerpt",
            "quote_payload",
            "feedback_history",
            "created_task",
            "dynamic_profile_update",
            "error_message",
            "created_at",
            "updated_at",
        )


class AITaskPricingSessionCreateSerializer(serializers.Serializer):
    task_payload = serializers.JSONField()


class AITaskPricingFeedbackSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("accept", "revise"))
    feedback_direction = serializers.ChoiceField(
        choices=("too_high", "too_low", "detail"),
        required=False,
        allow_blank=True,
    )
    feedback_text = serializers.CharField(
        required=False, allow_blank=True, max_length=1000
    )
