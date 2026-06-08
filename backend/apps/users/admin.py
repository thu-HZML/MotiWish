from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.ai.services import generate_daily_wish_refresh
from apps.common.timezones import business_localdate
from apps.users.models import DynamicProfile, StableProfile, User


class StableProfileInline(admin.StackedInline):
    model = StableProfile
    extra = 0
    can_delete = False


class DynamicProfileInline(admin.StackedInline):
    model = DynamicProfile
    extra = 0
    can_delete = False


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    actions = ("generate_daily_wish_candidates", "force_regenerate_daily_wish_candidates")
    list_display = (
        "id",
        "username",
        "email",
        "display_nickname",
        "gender",
        "occupation",
        "basic_profile_completed",
        "basic_profile_completion_score",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("gender", "occupation", "education_stage", "basic_profile_completed", "is_active", "is_staff")
    search_fields = ("username", "email", "nickname", "bio", "region")
    inlines = (StableProfileInline, DynamicProfileInline)
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "扩展信息",
            {
                "fields": (
                    "nickname",
                    "avatar",
                    "gender",
                    "birth_date",
                    "occupation",
                    "education_stage",
                    "language_preference",
                    "region",
                    "bio",
                    "timezone",
                    "long_term_goals",
                    "focus_areas",
                    "onboarding_completed",
                    "basic_profile_completed",
                    "basic_profile_completion_score",
                    "basic_profile_missing_fields",
                    "basic_profile_last_prompted_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    readonly_fields = (
        "basic_profile_completed",
        "basic_profile_completion_score",
        "basic_profile_missing_fields",
        "basic_profile_last_prompted_at",
        "created_at",
        "updated_at",
    )

    @admin.action(description="为选中用户生成今日 AI 愿望候选")
    def generate_daily_wish_candidates(self, request, queryset):
        self._generate_daily_wishes(request, queryset, force=False)

    @admin.action(description="为选中用户强制重刷今日 AI 愿望候选")
    def force_regenerate_daily_wish_candidates(self, request, queryset):
        self._generate_daily_wishes(request, queryset, force=True)

    def _generate_daily_wishes(self, request, queryset, *, force):
        refresh_date = business_localdate()
        created_count = 0
        reused_count = 0
        failed = []
        for user in queryset.filter(is_active=True):
            try:
                _, created = generate_daily_wish_refresh(
                    user=user,
                    refresh_date=refresh_date,
                    force=force,
                )
            except Exception as exc:
                failed.append(f"{user.username}: {str(exc)[:80]}")
                continue
            if created:
                created_count += 1
            else:
                reused_count += 1

        if failed:
            self.message_user(
                request,
                f"愿望候选生成完成：新增 {created_count}，复用 {reused_count}，失败 {len(failed)}。"
                f"失败示例：{'; '.join(failed[:3])}",
                level="warning",
            )
            return
        self.message_user(request, f"愿望候选生成完成：新增 {created_count}，复用 {reused_count}。")


@admin.register(StableProfile)
class StableProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_completed", "completion_score", "last_prompted_at", "questionnaire_completed_at")
    list_filter = ("is_completed", "reward_preference", "penalty_tolerance", "stress_sensitivity", "chronotype")
    search_fields = ("user__username", "user__email", "user__nickname")
    readonly_fields = ("is_completed", "completion_score", "missing_fields", "questionnaire_completed_at", "created_at", "updated_at")


@admin.register(DynamicProfile)
class DynamicProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "stress_level", "sleep_quality", "mood_state", "available_time_level", "last_prompted_at")
    list_filter = ("sleep_quality", "mood_state", "available_time_level")
    search_fields = ("user__username", "user__email", "user__nickname", "current_top_goal", "current_main_blocker")
    readonly_fields = ("created_at", "updated_at")
