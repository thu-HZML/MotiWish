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
