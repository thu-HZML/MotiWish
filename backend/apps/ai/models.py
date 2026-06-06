from django.db import models

from apps.common.models import TimeStampedModel


class AIReportJob(TimeStampedModel):
    class ReportType(models.TextChoices):
        DAILY = "daily", "日报"
        MONTHLY = "monthly", "月报"

    class Status(models.TextChoices):
        PENDING = "pending", "待生成"
        DONE = "done", "已完成"
        FAILED = "failed", "失败"

    owner = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="ai_report_jobs"
    )
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    summary = models.TextField(blank=True, verbose_name="报告摘要")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    prompt_context = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "AI 报告任务"
        verbose_name_plural = "AI 报告任务"
        ordering = ("-created_at", "-id")


class AIAgentRun(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "待执行"
        RUNNING = "running", "执行中"
        SUCCEEDED = "succeeded", "成功"
        FAILED = "failed", "失败"

    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="ai_agent_runs")
    workflow_key = models.CharField(max_length=64, verbose_name="工作流标识")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="状态")
    input_payload = models.JSONField(default=dict, blank=True, verbose_name="输入参数")
    context_payload = models.JSONField(default=dict, blank=True, verbose_name="上下文快照")
    state_payload = models.JSONField(default=dict, blank=True, verbose_name="状态数据")
    result_payload = models.JSONField(default=dict, blank=True, verbose_name="输出结果")
    error_message = models.CharField(max_length=255, blank=True, verbose_name="错误信息")
    trace_id = models.CharField(max_length=64, blank=True, verbose_name="追踪标识")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")

    class Meta:
        verbose_name = "AI Agent 运行记录"
        verbose_name_plural = "AI Agent 运行记录"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.workflow_key}:{self.status}:{self.owner_id}"


class AITaskPricingSession(TimeStampedModel):
    class Status(models.TextChoices):
        WAITING_FEEDBACK = "waiting_feedback", "等待反馈"
        ACCEPTED = "accepted", "已接受"
        CANCELLED = "cancelled", "已取消"
        FAILED = "failed", "失败"

    owner = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="ai_task_pricing_sessions"
    )
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.WAITING_FEEDBACK
    )
    task_payload = models.JSONField(default=dict, blank=True, verbose_name="任务草稿")
    profile_snapshot = models.JSONField(
        default=dict, blank=True, verbose_name="用户画像快照"
    )
    pricing_standard_version = models.CharField(
        max_length=32, default="task_pricing_v1"
    )
    pricing_standard_excerpt = models.TextField(blank=True, verbose_name="定价标准摘录")
    quote_payload = models.JSONField(default=dict, blank=True, verbose_name="当前定价")
    feedback_history = models.JSONField(
        default=list, blank=True, verbose_name="反馈历史"
    )
    created_task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pricing_sessions",
    )
    dynamic_profile_update = models.JSONField(
        default=dict, blank=True, verbose_name="动态画像更新"
    )
    error_message = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "AI任务定价会话"
        verbose_name_plural = "AI任务定价会话"
        ordering = ("-created_at", "-id")


class AIWishPricingSession(TimeStampedModel):
    class Status(models.TextChoices):
        WAITING_CONFIRMATION = "waiting_confirmation", "等待确认"
        ACCEPTED = "accepted", "已接受"
        CANCELLED = "cancelled", "已取消"
        FAILED = "failed", "失败"

    class Source(models.TextChoices):
        MANUAL = "manual", "用户手动愿望"
        DAILY_REFRESH = "daily_refresh", "每日刷新愿望"

    owner = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="ai_wish_pricing_sessions"
    )
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.MANUAL)
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.WAITING_CONFIRMATION
    )
    refresh_date = models.DateField(null=True, blank=True, db_index=True, verbose_name="刷新日期")
    wish_payload = models.JSONField(default=dict, blank=True, verbose_name="愿望草稿")
    context_snapshot = models.JSONField(default=dict, blank=True, verbose_name="上下文快照")
    profile_snapshot = models.JSONField(default=dict, blank=True, verbose_name="用户画像快照")
    pricing_standard_version = models.CharField(max_length=32, default="wish_pricing_v1")
    pricing_standard_excerpt = models.TextField(blank=True, verbose_name="定价标准摘录")
    quote_payload = models.JSONField(default=dict, blank=True, verbose_name="当前定价")
    generated_item = models.ForeignKey(
        "shop.WishItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wish_pricing_sessions",
    )
    error_message = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "AI愿望定价会话"
        verbose_name_plural = "AI愿望定价会话"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "source", "refresh_date"),
                condition=models.Q(source="daily_refresh", refresh_date__isnull=False),
                name="unique_daily_wish_refresh_per_user_date",
            ),
        ]
