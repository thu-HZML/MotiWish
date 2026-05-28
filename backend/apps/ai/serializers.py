from rest_framework import serializers

from apps.ai.models import AIReportJob, AITaskPricingSession
from apps.tasks.models import DifficultyLevel, RecurrenceType, SettlementTrack, TaskType
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


class TaskPricingDraftSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, help_text="任务标题。")
    description = serializers.CharField(required=False, allow_blank=True, default="", help_text="任务详细说明。")
    task_type = serializers.ChoiceField(choices=TaskType.choices, help_text="任务类型：daily / recurring / one_time。")
    recurrence = serializers.ChoiceField(
        choices=RecurrenceType.choices,
        required=False,
        default=RecurrenceType.NONE,
        help_text="重复规则：none / daily / weekly / monthly。",
    )
    settlement_track = serializers.ChoiceField(
        choices=SettlementTrack.choices,
        required=False,
        default=SettlementTrack.REGULAR,
        help_text="结算轨道：regular 常规轨道；exploration 探索轨道。",
    )
    difficulty_level = serializers.ChoiceField(
        choices=DifficultyLevel.choices,
        required=False,
        default=DifficultyLevel.MEDIUM,
        help_text="难度：low / medium / high。",
    )
    estimated_focus_minutes = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="探索轨道必填，表示预计专注分钟数。",
    )
    weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        default=list,
        help_text="weekly 任务使用，0=周一，6=周日。",
    )
    month_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=31),
        required=False,
        default=list,
        help_text="monthly 任务使用，例如 [1, 15, 28]。",
    )
    metric_key = serializers.CharField(required=False, allow_blank=True, max_length=50, default="")
    target_value = serializers.IntegerField(required=False, allow_null=True, default=None)
    progress_target = serializers.IntegerField(required=False, min_value=1, default=100)
    starts_on = serializers.DateField(required=False, allow_null=True)
    ends_on = serializers.DateField(required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    ai_metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        task_type = attrs["task_type"]
        recurrence = attrs.get("recurrence", RecurrenceType.NONE)
        settlement_track = attrs.get("settlement_track", SettlementTrack.REGULAR)

        if attrs.get("starts_on") and attrs.get("ends_on") and attrs["starts_on"] > attrs["ends_on"]:
            raise serializers.ValidationError({"ends_on": "ends_on 不能早于 starts_on。"})
        if task_type == TaskType.ONE_TIME and recurrence != RecurrenceType.NONE:
            raise serializers.ValidationError({"recurrence": "one_time 任务不能设置重复规则。"})
        if recurrence == RecurrenceType.WEEKLY and not attrs.get("weekdays"):
            raise serializers.ValidationError({"weekdays": "weekly 任务必须提供 weekdays。"})
        if recurrence != RecurrenceType.WEEKLY and attrs.get("weekdays"):
            raise serializers.ValidationError({"weekdays": "只有 weekly 任务应填写 weekdays。"})
        if recurrence == RecurrenceType.MONTHLY and not attrs.get("month_days"):
            raise serializers.ValidationError({"month_days": "monthly 任务必须提供 month_days。"})
        if recurrence != RecurrenceType.MONTHLY and attrs.get("month_days"):
            raise serializers.ValidationError({"month_days": "只有 monthly 任务应填写 month_days。"})
        if settlement_track == SettlementTrack.EXPLORATION and not attrs.get("estimated_focus_minutes"):
            raise serializers.ValidationError({"estimated_focus_minutes": "探索轨道必须提供 estimated_focus_minutes。"})
        if settlement_track == SettlementTrack.EXPLORATION and task_type == TaskType.DAILY:
            raise serializers.ValidationError({"task_type": "探索轨道不建议用于 daily 任务。"})
        return attrs


class AITaskPricingSessionCreateSerializer(serializers.Serializer):
    task_payload = TaskPricingDraftSerializer(help_text="待定价任务草稿。")


class AITaskPricingFeedbackSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=("accept", "revise"),
        help_text="accept 表示接受当前定价并创建任务；revise 表示提交反馈并重新定价。",
    )
    feedback_direction = serializers.ChoiceField(
        choices=("too_high", "too_low", "detail"),
        required=False,
        allow_blank=True,
        help_text="revise 时可传：too_high 偏高；too_low 偏低；detail 详细说明。",
    )
    feedback_text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="用户对当前定价的自然语言反馈。",
    )

    def validate(self, attrs):
        if attrs["action"] == "revise" and not attrs.get("feedback_direction") and not attrs.get("feedback_text"):
            raise serializers.ValidationError("revise 至少需要 feedback_direction 或 feedback_text。")
        return attrs
