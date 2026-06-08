from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.timezones import format_business_datetime
from apps.tasks.models import DifficultyLevel, SettlementTrack, Task, TaskOccurrence
from apps.tasks.pricing import DIFFICULTY_FACTORS, build_pricing_context


class TaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=120, help_text="任务标题。")
    description = serializers.CharField(required=False, allow_blank=True, help_text="任务说明，可为空。")
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False, help_text="周任务使用，0 表示周一，6 表示周日。")
    month_days = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=31), required=False, help_text="月任务使用，例如 [1, 15, 28]。")
    metric_key = serializers.CharField(required=False, allow_blank=True, max_length=50, help_text="进度目标标识，可为空。")
    target_value = serializers.IntegerField(required=False, allow_null=True, help_text="进度目标值，可为空。")
    estimated_focus_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=0, help_text="探索轨道任务预计专注时长，分钟。")
    pricing_snapshot = serializers.JSONField(read_only=True, help_text="后端定价上下文快照。")

    class Meta:
        model = Task
        fields = ("id", "title", "description", "task_type", "recurrence", "settlement_track", "difficulty_level", "estimated_focus_minutes", "weekdays", "month_days", "metric_key", "target_value", "progress_target", "reward_primary", "penalty_primary", "pricing_status", "pricing_requested_at", "pricing_resolved_at", "pricing_snapshot", "starts_on", "ends_on", "due_at", "status", "tags", "ai_metadata", "created_at", "updated_at")
        read_only_fields = ("pricing_status", "pricing_requested_at", "pricing_resolved_at", "pricing_snapshot", "created_at", "updated_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_time_fields = (instance.pricing_snapshot or {}).get("user_time_fields") or {}
        for field in ("starts_on", "ends_on"):
            if user_time_fields.get(field):
                data[field] = user_time_fields[field]
        due_at = format_business_datetime(user_time_fields.get("due_at") or instance.due_at)
        if due_at:
            data["due_at"] = due_at
        return data

    def _raw_user_time_fields(self):
        initial_data = getattr(self, "initial_data", {}) or {}
        return {
            field: initial_data[field]
            for field in ("starts_on", "ends_on", "due_at")
            if initial_data.get(field) not in (None, "")
        }

    def _merge_user_time_fields(self, instance):
        user_time_fields = self._raw_user_time_fields()
        if not user_time_fields:
            return instance
        instance.pricing_snapshot = {
            **(instance.pricing_snapshot or {}),
            "user_time_fields": {
                **((instance.pricing_snapshot or {}).get("user_time_fields") or {}),
                **user_time_fields,
            },
        }
        instance.save(update_fields=["pricing_snapshot", "updated_at"])
        return instance

    def create(self, validated_data):
        instance = super().create(validated_data)
        return self._merge_user_time_fields(instance)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return self._merge_user_time_fields(instance)

    def validate(self, attrs):
        task_type = attrs.get("task_type", getattr(self.instance, "task_type", None))
        recurrence = attrs.get("recurrence", getattr(self.instance, "recurrence", "none"))
        settlement_track = attrs.get("settlement_track", getattr(self.instance, "settlement_track", SettlementTrack.REGULAR))
        weekdays = attrs.get("weekdays", getattr(self.instance, "weekdays", []))
        month_days = attrs.get("month_days", getattr(self.instance, "month_days", []))
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        estimated_focus_minutes = attrs.get("estimated_focus_minutes", getattr(self.instance, "estimated_focus_minutes", None))
        if task_type == "daily":
            raise serializers.ValidationError({"task_type": "daily is reserved for daily metrics; use /api/v1/daily/evaluate/."})
        if starts_on and ends_on and starts_on > ends_on:
            raise serializers.ValidationError("参数不符合要求。")
        if recurrence == "weekly" and not weekdays:
            raise serializers.ValidationError({"weekdays": "参数不符合要求。"})
        if recurrence != "weekly" and "weekdays" in attrs and weekdays:
            raise serializers.ValidationError({"weekdays": "参数不符合要求。"})
        if recurrence == "monthly" and not month_days:
            raise serializers.ValidationError({"month_days": "参数不符合要求。"})
        if recurrence != "monthly" and "month_days" in attrs and month_days:
            raise serializers.ValidationError({"month_days": "参数不符合要求。"})
        if task_type == "one_time" and recurrence != "none":
            raise serializers.ValidationError({"recurrence": "参数不符合要求。"})
        if settlement_track == SettlementTrack.EXPLORATION and not estimated_focus_minutes:
            raise serializers.ValidationError({"estimated_focus_minutes": "必填。"})
        if settlement_track == SettlementTrack.EXPLORATION and task_type == "daily":
            raise serializers.ValidationError({"task_type": "参数不符合要求。"})
        return attrs


class TaskUpdateSerializer(TaskSerializer):
    progress = serializers.IntegerField(required=False, min_value=0, write_only=True, help_text="任务实例实际进度，默认更新今天。")
    occurrence_date = serializers.DateField(required=False, write_only=True, help_text="更新进度任务实例日期，progress。")

    class Meta(TaskSerializer.Meta):
        fields = (*(field for field in TaskSerializer.Meta.fields if field != "progress_target"), "progress", "occurrence_date")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "progress_target" in self.initial_data:
            raise serializers.ValidationError({"progress_target": "参数不符合要求。"})
        if "occurrence_date" in attrs and "progress" not in attrs:
            raise serializers.ValidationError({"progress": "必填。"})
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
    task = TaskSerializer(read_only=True, help_text="任务模板。")
    settlement_details = serializers.SerializerMethodField(help_text="任务结算明细：奖励、惩罚、周期完成率。")

    class Meta:
        model = TaskOccurrence
        fields = ("id", "task", "occurrence_date", "status", "progress", "settled_at", "reward_transaction_id", "penalty_transaction_id", "settlement_details", "created_at", "updated_at")

    @extend_schema_field(serializers.JSONField)
    def get_settlement_details(self, obj):
        if hasattr(obj, "_settlement_details"):
            return obj._settlement_details
        transaction = obj.penalty_transaction or obj.reward_transaction
        return transaction.payload if transaction else {}


class TaskActionSerializer(serializers.Serializer):
    occurrence_date = serializers.DateField(required=False, help_text="任务实例日期，今天。")
    progress = serializers.IntegerField(required=False, min_value=0, help_text="当前进度值，探索轨道任务使用分钟。")
    settle_period = serializers.BooleanField(required=False, default=False, help_text="周期结算，true 返回惩罚明细。")


class TaskProgressUpdateSerializer(serializers.Serializer):
    occurrence_date = serializers.DateField(required=False, help_text="任务实例日期，今天。")
    progress = serializers.IntegerField(min_value=0, help_text="任务实例实际进度，不能超过 progress_target。")


class TaskPricingPreviewSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=120, default="", help_text="定价任务标题。")
    description = serializers.CharField(required=False, allow_blank=True, default="", help_text="定价任务说明。")
    task_type = serializers.ChoiceField(choices=Task._meta.get_field("task_type").choices, help_text="任务类型。")
    recurrence = serializers.ChoiceField(choices=Task._meta.get_field("recurrence").choices, required=False, default="none", help_text="重复规则。")
    settlement_track = serializers.ChoiceField(choices=SettlementTrack.choices, default=SettlementTrack.REGULAR, help_text="结算轨道: regular=常规轨道, exploration=探索轨道。")
    difficulty_level = serializers.ChoiceField(choices=DifficultyLevel.choices, required=False, default=DifficultyLevel.MEDIUM, help_text="任务难度，后端自动估算。")
    auto_estimate_difficulty = serializers.BooleanField(required=False, default=True, help_text="自动估算任务难度。")
    estimated_focus_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=0, help_text="探索轨道任务预计专注时长，分钟。")
    progress_target = serializers.IntegerField(required=False, min_value=0, default=100, help_text="任务进度目标。")
    metric_key = serializers.CharField(required=False, allow_blank=True, max_length=50, default="", help_text="进度目标标识。")
    target_value = serializers.IntegerField(required=False, allow_null=True, default=None, help_text="进度目标值。")
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False, default=list, help_text="周任务使用日期，0 表示周一。")
    month_days = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=31), required=False, default=list, help_text="月任务使用日期。")
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list, help_text="任务标签。")

    def validate(self, attrs):
        if attrs["settlement_track"] == SettlementTrack.EXPLORATION and not attrs.get("estimated_focus_minutes"):
            raise serializers.ValidationError({"estimated_focus_minutes": "必填。"})
        return attrs


class TaskPricingPreviewPayloadSerializer(serializers.Serializer):
    settlement_track = serializers.ChoiceField(choices=SettlementTrack.choices, help_text="结算轨道。")
    task_type = serializers.ChoiceField(choices=Task._meta.get_field("task_type").choices, help_text="任务类型。")
    formula = serializers.CharField(help_text="定价公式。")
    normalized_payload = serializers.JSONField(help_text="后端任务定价上下文。")
    difficulty_factor_hint = serializers.IntegerField(required=False, help_text="探索轨道难度系数提示。")


def build_preview_response(validated_data):
    context = build_pricing_context(task_data=validated_data)
    response = {"settlement_track": context.settlement_track, "task_type": context.task_type, "formula": context.formula, "normalized_payload": context.normalized_payload}
    if context.settlement_track == SettlementTrack.EXPLORATION:
        difficulty_level = context.normalized_payload.get("difficulty_level", validated_data.get("difficulty_level", DifficultyLevel.MEDIUM))
        response["difficulty_factor_hint"] = DIFFICULTY_FACTORS.get(difficulty_level, DIFFICULTY_FACTORS[DifficultyLevel.MEDIUM])
    return response
