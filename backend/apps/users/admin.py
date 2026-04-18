from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("id", "username", "email", "nickname", "is_active", "is_staff", "created_at")
    search_fields = ("username", "email", "nickname")
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "扩展信息",
            {"fields": ("nickname", "timezone", "onboarding_completed", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")
