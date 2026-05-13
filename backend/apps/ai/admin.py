from django.contrib import admin

from apps.ai.models import AIReportJob, AITaskPricingSession


@admin.register(AIReportJob)
class AIReportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "report_type", "status", "created_at")
    list_filter = ("report_type", "status")


@admin.register(AITaskPricingSession)
class AITaskPricingSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "status", "created_task", "created_at", "updated_at")
    list_filter = ("status", "pricing_standard_version")
    search_fields = ("owner__username", "owner__email", "task_payload", "quote_payload")
    raw_id_fields = ("owner", "created_task")
    readonly_fields = ("created_at", "updated_at")
