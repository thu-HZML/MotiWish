from django.contrib import admin

from apps.ai.models import AIReportJob, AITaskPricingSession, AIWishPricingSession
from apps.ai.services import accept_wish_pricing_session, cancel_wish_pricing_session


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
    actions = ("accept_wish_candidates", "cancel_wish_candidates")
    list_display = ("id", "owner", "source", "status", "refresh_date", "generated_item", "created_at", "updated_at")
    list_filter = ("source", "status", "pricing_standard_version", "refresh_date")
    search_fields = ("owner__username", "owner__email", "wish_payload", "quote_payload")
    raw_id_fields = ("owner", "generated_item")
    readonly_fields = ("created_at", "updated_at")

    @admin.action(description="确认选中的愿望候选并创建商品")
    def accept_wish_candidates(self, request, queryset):
        success_count = 0
        failed = []
        for session in queryset:
            try:
                accept_wish_pricing_session(session=session)
                success_count += 1
            except Exception as exc:
                failed.append(f"#{session.id}: {str(exc)[:80]}")
        if failed:
            self.message_user(
                request,
                f"确认完成：成功 {success_count}，失败 {len(failed)}。失败示例：{'; '.join(failed[:3])}",
                level="warning",
            )
            return
        self.message_user(request, f"确认完成：成功创建 {success_count} 个愿望商品。")

    @admin.action(description="取消选中的愿望候选")
    def cancel_wish_candidates(self, request, queryset):
        success_count = 0
        failed = []
        for session in queryset:
            try:
                cancel_wish_pricing_session(session=session)
                success_count += 1
            except Exception as exc:
                failed.append(f"#{session.id}: {str(exc)[:80]}")
        if failed:
            self.message_user(
                request,
                f"取消完成：成功 {success_count}，失败 {len(failed)}。失败示例：{'; '.join(failed[:3])}",
                level="warning",
            )
            return
        self.message_user(request, f"取消完成：成功取消 {success_count} 个愿望候选。")
