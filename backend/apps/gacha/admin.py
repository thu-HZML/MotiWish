from django.contrib import admin

from apps.gacha.models import GachaDrawRecord, GachaPool, GachaPoolUserState


@admin.register(GachaPool)
class GachaPoolAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "cost_primary",
        "common_reward",
        "rare_reward",
        "epic_reward",
        "legendary_reward",
        "is_active",
    )


@admin.register(GachaPoolUserState)
class GachaPoolUserStateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "pool",
        "total_draws",
        "draws_since_rare",
        "draws_since_epic",
        "draws_since_legendary",
        "updated_at",
    )
    search_fields = ("owner__username", "owner__email", "pool__name")


@admin.register(GachaDrawRecord)
class GachaDrawRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "pool", "cost_primary", "reward_secondary", "reward_tier", "pity_tier", "created_at")
    list_filter = ("pool", "reward_tier", "pity_tier")
