from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

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
