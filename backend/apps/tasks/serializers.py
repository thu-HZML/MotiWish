from rest_framework import serializers

from apps.tasks.models import (
    DifficultyLevel,
    PricingStatus,
    SettlementTrack,
    Task,
    TaskOccurrence,
)
from apps.tasks.pricing import DIFFICULTY_FACTORS, build_pricing_context


class TaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=120, help_text="任务标题。")
    description = serializers.CharField(required=False, allow_blank=True, help_text="任务详细说明，可为空。")
    weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        help_text="weekly 任务使用，0=周一，6=周日。",
    )
    month_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=31),
        required=False,
        help_text="monthly 任务使用，例如 [1, 15, 28]。",
    )
    metric_key = serializers.CharField(required=False, allow_blank=True, max_length=50)
    target_value = serializers.IntegerField(required=False, allow_null=True)
    estimated_focus_minutes = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="探索轨道任务可填写的预估专注时长（分钟）。",
    )
    pricing_snapshot = serializers.JSONField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "task_type",
            "recurrence",
            "settlement_track",
            "difficulty_level",
            "estimated_focus_minutes",
            "weekdays",
            "month_days",
            "metric_key",
            "target_value",
            "progress_target",
            "reward_primary",
            "penalty_primary",
            "pricing_status",
            "pricing_requested_at",
            "pricing_resolved_at",
            "pricing_snapshot",
            "starts_on",
            "ends_on",
            "due_at",
            "status",
            "tags",
            "ai_metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "pricing_status",
            "pricing_requested_at",
            "pricing_resolved_at",
            "pricing_snapshot",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        task_type = attrs.get("task_type", getattr(self.instance, "task_type", None))
        recurrence = attrs.get("recurrence", getattr(self.instance, "recurrence", "none"))
        settlement_track = attrs.get(
            "settlement_track",
            getattr(self.instance, "settlement_track", SettlementTrack.REGULAR),
        )
        weekdays = attrs.get("weekdays", getattr(self.instance, "weekdays", []))
        month_days = attrs.get("month_days", getattr(self.instance, "month_days", []))
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        estimated_focus_minutes = attrs.get(
            "estimated_focus_minutes",
            getattr(self.instance, "estimated_focus_minutes", None),
        )

        if starts_on and ends_on and starts_on > ends_on:
            raise serializers.ValidationError("starts_on 不能晚于 ends_on。")

        if recurrence == "weekly" and not weekdays:
            raise serializers.ValidationError({"weekdays": "weekly 任务必须提供 weekdays。"})

        if recurrence != "weekly" and "weekdays" in attrs and weekdays:
            raise serializers.ValidationError({"weekdays": "只有 weekly 任务才应填写 weekdays。"})

        if recurrence == "monthly" and not month_days:
            raise serializers.ValidationError({"month_days": "monthly 任务必须提供 month_days。"})

        if recurrence != "monthly" and "month_days" in attrs and month_days:
            raise serializers.ValidationError({"month_days": "只有 monthly 任务才应填写 month_days。"})

        if task_type == "one_time" and recurrence != "none":
            raise serializers.ValidationError({"recurrence": "one_time 任务不能再设置重复规则。"})

        if settlement_track == SettlementTrack.EXPLORATION and not estimated_focus_minutes:
            raise serializers.ValidationError(
                {"estimated_focus_minutes": "探索轨道任务必须提供 estimated_focus_minutes。"}
            )

        if settlement_track == SettlementTrack.EXPLORATION and task_type == "daily":
            raise serializers.ValidationError({"task_type": "探索轨道不建议用于 daily 任务。"})

        return attrs


class TaskUpdateSerializer(TaskSerializer):
    progress = serializers.IntegerField(
        required=False,
        min_value=0,
        write_only=True,
        help_text="任务实例的实际完成进度，默认更新今天的任务实例。",
    )
    occurrence_date = serializers.DateField(
        required=False,
        write_only=True,
        help_text="要更新进度的任务实例日期，仅在同时提交 progress 时使用。",
    )

    class Meta(TaskSerializer.Meta):
        fields = (
            *(field for field in TaskSerializer.Meta.fields if field != "progress_target"),
            "progress",
            "occurrence_date",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "progress_target" in self.initial_data:
            raise serializers.ValidationError(
                {"progress_target": "更新任务时不能修改进度目标；请使用 progress 更新实际进度。"}
            )
        if "occurrence_date" in attrs and "progress" not in attrs:
            raise serializers.ValidationError({"progress": "提交 occurrence_date 时必须同时提交 progress。"})
        return attrs

    def update(self, instance, validated_data):
        progress = validated_data.pop("progress", None)
        occurrence_date = validated_data.pop("occurrence_date", None)
        instance = super().update(instance, validated_data)
        if progress is not None:
            from apps.tasks.services import update_task_progress

            update_task_progress(task=instance, progress=progress, target_date=occurrence_date)
        return instance


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
    occurrence_date = serializers.DateField(required=False, help_text="要结算的任务实例日期，默认今天。")
    progress = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="本次完成时写入的进度值；不传则自动使用任务的 progress_target。",
    )


class TaskProgressUpdateSerializer(serializers.Serializer):
    occurrence_date = serializers.DateField(
        required=False,
        help_text="要更新进度的任务实例日期，默认今天。",
    )
    progress = serializers.IntegerField(
        min_value=0,
        help_text="任务实例的实际完成进度，不能超过任务的 progress_target。",
    )


class TaskPricingPreviewSerializer(serializers.Serializer):
    task_type = serializers.ChoiceField(choices=Task._meta.get_field("task_type").choices)
    recurrence = serializers.ChoiceField(
        choices=Task._meta.get_field("recurrence").choices,
        required=False,
        default="none",
    )
    settlement_track = serializers.ChoiceField(choices=SettlementTrack.choices, default=SettlementTrack.REGULAR)
    difficulty_level = serializers.ChoiceField(
        choices=DifficultyLevel.choices,
        required=False,
        default=DifficultyLevel.MEDIUM,
    )
    estimated_focus_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    progress_target = serializers.IntegerField(required=False, min_value=0, default=100)
    metric_key = serializers.CharField(required=False, allow_blank=True, max_length=50, default="")
    target_value = serializers.IntegerField(required=False, allow_null=True, default=None)
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False, default=list)
    month_days = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=31), required=False, default=list)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)

    def validate(self, attrs):
        if attrs["settlement_track"] == SettlementTrack.EXPLORATION and not attrs.get("estimated_focus_minutes"):
            raise serializers.ValidationError(
                {"estimated_focus_minutes": "探索轨道预览必须提供 estimated_focus_minutes。"}
            )
        return attrs


class TaskPricingPreviewPayloadSerializer(serializers.Serializer):
    settlement_track = serializers.ChoiceField(choices=SettlementTrack.choices)
    task_type = serializers.ChoiceField(choices=Task._meta.get_field("task_type").choices)
    formula = serializers.CharField()
    normalized_payload = serializers.JSONField()
    difficulty_factor_hint = serializers.IntegerField(required=False)


class TaskPricingApplySerializer(serializers.Serializer):
    reward_primary = serializers.IntegerField(min_value=0, help_text="AI 产出的一级货币奖励。")
    penalty_primary = serializers.IntegerField(min_value=0, help_text="AI 产出的一级货币惩罚。")
    pricing_payload = serializers.JSONField(
        required=False,
        help_text="AI 回写的完整定价结果，可包含理由、置信度、分段信息等。",
    )


class TaskPricingMetaSerializer(serializers.Serializer):
    settlement_tracks = serializers.JSONField()
    formulas = serializers.JSONField()
    difficulty_factors = serializers.JSONField()


def build_preview_response(validated_data):
    context = build_pricing_context(task_data=validated_data)
    response = {
        "settlement_track": context.settlement_track,
        "task_type": context.task_type,
        "formula": context.formula,
        "normalized_payload": context.normalized_payload,
    }
    if context.settlement_track == SettlementTrack.EXPLORATION:
        response["difficulty_factor_hint"] = DIFFICULTY_FACTORS.get(
            validated_data.get("difficulty_level", DifficultyLevel.MEDIUM),
            DIFFICULTY_FACTORS[DifficultyLevel.MEDIUM],
        )
    return response
