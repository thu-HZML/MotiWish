from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "display_nickname",
        "gender",
        "occupation",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("gender", "occupation", "is_active", "is_staff")
    search_fields = ("username", "email", "nickname", "bio")
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
                    "bio",
                    "timezone",
                    "onboarding_completed",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")
