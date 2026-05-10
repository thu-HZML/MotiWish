from django.db import models

from apps.common.models import TimeStampedModel, UserOwnedModel


class TaskType(models.TextChoices):
    DAILY = "daily", "日常任务"
    RECURRING = "recurring", "周期任务"
    ONE_TIME = "one_time", "一次性任务"


class RecurrenceType(models.TextChoices):
    NONE = "none", "不重复"
    DAILY = "daily", "每天"
    WEEKLY = "weekly", "每周"
    MONTHLY = "monthly", "每月"


class TaskStatus(models.TextChoices):
    ACTIVE = "active", "启用"
    ARCHIVED = "archived", "归档"


class OccurrenceStatus(models.TextChoices):
    PENDING = "pending", "待完成"
    COMPLETED = "completed", "已完成"
    MISSED = "missed", "已错过"
    CANCELLED = "cancelled", "已取消"


class SettlementTrack(models.TextChoices):
    REGULAR = "regular", "常规轨道"
    EXPLORATION = "exploration", "探索轨道"


class DifficultyLevel(models.TextChoices):
    LOW = "low", "低"
    MEDIUM = "medium", "中"
    HIGH = "high", "高"


class PricingStatus(models.TextChoices):
    UNPRICED = "unpriced", "未定价"
    PENDING = "pending", "待 AI 定价"
    QUOTED = "quoted", "已生成报价"
    APPLIED = "applied", "已应用报价"


class Task(UserOwnedModel):
    title = models.CharField(max_length=120, verbose_name="任务标题")
    description = models.TextField(blank=True, verbose_name="任务描述")
    task_type = models.CharField(max_length=20, choices=TaskType.choices, verbose_name="任务类型")
    recurrence = models.CharField(max_length=20, choices=RecurrenceType.choices, default=RecurrenceType.NONE)
    settlement_track = models.CharField(
        max_length=20,
        choices=SettlementTrack.choices,
        default=SettlementTrack.REGULAR,
        verbose_name="结算轨道",
    )
    difficulty_level = models.CharField(
        max_length=16,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM,
        verbose_name="难度等级",
    )
    estimated_focus_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name="预估专注时长（分钟）")
    weekdays = models.JSONField(default=list, blank=True, verbose_name="周重复设置")
    month_days = models.JSONField(default=list, blank=True, verbose_name="月重复设置")
    metric_key = models.CharField(max_length=50, blank=True, verbose_name="系统指标键")
    target_value = models.IntegerField(null=True, blank=True, verbose_name="目标值")
    progress_target = models.PositiveIntegerField(default=100, verbose_name="进度目标")
    reward_primary = models.PositiveIntegerField(default=0, verbose_name="一级货币奖励")
    penalty_primary = models.PositiveIntegerField(default=0, verbose_name="一级货币惩罚")
    pricing_status = models.CharField(
        max_length=20,
        choices=PricingStatus.choices,
        default=PricingStatus.UNPRICED,
        verbose_name="定价状态",
    )
    pricing_requested_at = models.DateTimeField(null=True, blank=True, verbose_name="发起定价时间")
    pricing_resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="完成定价时间")
    pricing_snapshot = models.JSONField(default=dict, blank=True, verbose_name="定价快照")
    starts_on = models.DateField(null=True, blank=True, verbose_name="开始日期")
    ends_on = models.DateField(null=True, blank=True, verbose_name="结束日期")
    due_at = models.DateTimeField(null=True, blank=True, verbose_name="截止时间")
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.ACTIVE)
    tags = models.JSONField(default=list, blank=True, verbose_name="标签")
    ai_metadata = models.JSONField(default=dict, blank=True, verbose_name="AI 元数据")

    class Meta:
        verbose_name = "任务"
        verbose_name_plural = "任务"
        ordering = ("-created_at", "-id")


class TaskOccurrence(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="occurrences", verbose_name="任务")
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="task_occurrences")
    occurrence_date = models.DateField(verbose_name="发生日期")
    status = models.CharField(max_length=20, choices=OccurrenceStatus.choices, default=OccurrenceStatus.PENDING)
    progress = models.PositiveIntegerField(default=0, verbose_name="完成进度")
    settled_at = models.DateTimeField(null=True, blank=True, verbose_name="结算时间")
    reward_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    penalty_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "任务实例"
        verbose_name_plural = "任务实例"
        unique_together = ("task", "occurrence_date")
        ordering = ("-occurrence_date", "-id")
