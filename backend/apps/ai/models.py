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

    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="ai_report_jobs")
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    summary = models.TextField(blank=True, verbose_name="报告摘要")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    prompt_context = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "AI报告任务"
        verbose_name_plural = "AI报告任务"
        ordering = ("-created_at", "-id")
