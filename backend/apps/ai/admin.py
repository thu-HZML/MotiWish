from django.contrib import admin

from apps.ai.models import AIAgentRun, AIReportJob


@admin.register(AIReportJob)
class AIReportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "report_type", "status", "created_at")
    list_filter = ("report_type", "status")


@admin.register(AIAgentRun)
class AIAgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "workflow_key", "status", "trace_id", "created_at")
    list_filter = ("workflow_key", "status")
    search_fields = ("trace_id", "owner__username", "workflow_key")
