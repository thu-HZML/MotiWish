from django.contrib import admin

from apps.ai.models import AIReportJob, AITaskPricingSession, AIWishPricingSession


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


@admin.register(AIWishPricingSession)
class AIWishPricingSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "source", "status", "refresh_date", "generated_item", "created_at", "updated_at")
    list_filter = ("source", "status", "pricing_standard_version", "refresh_date")
    search_fields = ("owner__username", "owner__email", "wish_payload", "quote_payload")
    raw_id_fields = ("owner", "generated_item")
    readonly_fields = ("created_at", "updated_at")
