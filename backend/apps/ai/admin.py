from django.contrib import admin

from apps.ai.models import AIReportJob


@admin.register(AIReportJob)
class AIReportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "report_type", "status", "created_at")
    list_filter = ("report_type", "status")
