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
