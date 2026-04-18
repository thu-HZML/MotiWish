from django.contrib import admin

from apps.gacha.models import GachaDrawRecord, GachaPool


@admin.register(GachaPool)
class GachaPoolAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cost_primary", "base_secondary_reward", "pity_threshold", "is_active")


@admin.register(GachaDrawRecord)
class GachaDrawRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "pool", "cost_primary", "reward_secondary", "multiplier", "created_at")
    list_filter = ("pool", "is_bonus", "is_jackpot", "is_pity")
