from rest_framework import serializers

from apps.tasks.models import Task, TaskOccurrence


class TaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=120,
        help_text="任务标题，建议用一句简短动作描述，例如“背单词 30 分钟”。",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="任务详细说明，可为空。",
    )
    task_type = serializers.ChoiceField(
        choices=Task._meta.get_field("task_type").choices,
        help_text="任务类型：daily=日常任务，recurring=周期任务，one_time=一次性任务。",
    )
    recurrence = serializers.ChoiceField(
        choices=Task._meta.get_field("recurrence").choices,
        required=False,
        help_text="重复规则：none=不重复，daily=每天，weekly=每周，monthly=每月。daily 任务通常可保持 none。",
    )
    weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        help_text="每周重复时生效，使用 Python weekday 编码：0=周一，1=周二，...，6=周日。",
    )
    month_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=31),
        required=False,
        help_text="每月重复时生效，填写每月的第几天，例如 [1, 15, 28]。",
    )
    metric_key = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="可选的系统指标键，用于后续接入打卡统计、AI 分析或自动进度汇总。",
    )
    target_value = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="指标目标值，可与 metric_key 搭配使用，例如目标步数、目标时长。",
    )
    progress_target = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text="任务完成时默认写入的进度值，complete 接口未传 progress 时会使用它。",
    )
    reward_primary = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text="完成任务后奖励的一级货币数量。",
    )
    penalty_primary = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text="预留的惩罚金额。当前完成任务逻辑会发奖励，但尚未自动执行超时扣罚。",
    )
    starts_on = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="任务生效开始日期，留空表示立即生效。",
    )
    ends_on = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="任务生效结束日期，留空表示长期有效。",
    )
    due_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="一次性任务的截止时间。当前系统会让 one_time 任务从生效日起到 due_at 当天每天都出现。",
    )
    status = serializers.ChoiceField(
        choices=Task._meta.get_field("status").choices,
        required=False,
        help_text="任务状态：active=启用，archived=归档。归档任务不会再生成新的任务实例。",
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        help_text="可选标签列表，例如 [\"study\", \"health\"]。",
    )
    ai_metadata = serializers.JSONField(
        required=False,
        help_text="AI 扩展元数据，预留给评分、推荐、标签推断等能力。",
    )

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

    def validate(self, attrs):
        task_type = attrs.get("task_type", getattr(self.instance, "task_type", None))
        recurrence = attrs.get("recurrence", getattr(self.instance, "recurrence", "none"))
        weekdays = attrs.get("weekdays", getattr(self.instance, "weekdays", []))
        month_days = attrs.get("month_days", getattr(self.instance, "month_days", []))
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))

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

        return attrs


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
    occurrence_date = serializers.DateField(
        required=False,
        help_text="要结算的任务实例日期，默认是今天。",
    )
    progress = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="本次完成时写入的进度值；不传则自动使用任务的 progress_target。",
    )
