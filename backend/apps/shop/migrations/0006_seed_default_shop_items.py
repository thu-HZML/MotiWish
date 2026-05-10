from django.conf import settings
from django.db import migrations


DEFAULT_SHOP_ITEMS = [
    {
        "catalog_key": "exp_pack_small",
        "title": "小份经验书",
        "description": "购买后立即获得 50 点经验，适合日常补一点成长进度。",
        "category": "growth_material",
        "item_kind": "experience_pack",
        "rarity": "common",
        "source": "system",
        "price_tier": "small",
        "price_secondary": 40,
        "inventory": None,
        "is_enabled": True,
        "is_stackable": True,
        "effect_payload": {"experience": 50},
    },
    {
        "catalog_key": "exp_pack_medium",
        "title": "中份经验书",
        "description": "购买后立即获得 160 点经验，适合作为主力养成材料。",
        "category": "growth_material",
        "item_kind": "experience_pack",
        "rarity": "rare",
        "source": "system",
        "price_tier": "small",
        "price_secondary": 120,
        "inventory": None,
        "is_enabled": True,
        "is_stackable": True,
        "effect_payload": {"experience": 160},
    },
    {
        "catalog_key": "exp_pack_large",
        "title": "大份经验书",
        "description": "购买后立即获得 450 点经验，适合中期集中推进等级。",
        "category": "growth_material",
        "item_kind": "experience_pack",
        "rarity": "epic",
        "source": "system",
        "price_tier": "medium",
        "price_secondary": 300,
        "inventory": None,
        "is_enabled": True,
        "is_stackable": True,
        "effect_payload": {"experience": 450},
    },
    {
        "catalog_key": "debt_repayment_card_standard",
        "title": "还债卡",
        "description": "购买后进入库存。使用时清空当前一级货币负债；没有负债时不能使用。",
        "category": "utility_item",
        "item_kind": "debt_repayment_card",
        "rarity": "rare",
        "source": "system",
        "price_tier": "medium",
        "price_secondary": 180,
        "inventory": None,
        "is_enabled": True,
        "is_stackable": True,
        "effect_payload": {"effect": "debt_reset"},
    },
    {
        "catalog_key": "task_failure_protection_card",
        "title": "任务失败保护卡",
        "description": "规划中的道具：未来用于抵消一次任务失败惩罚。",
        "category": "utility_item",
        "item_kind": "task_failure_protection_card",
        "rarity": "rare",
        "source": "system",
        "price_tier": "small",
        "price_secondary": 100,
        "inventory": None,
        "is_enabled": False,
        "is_stackable": True,
        "effect_payload": {"effect": "cancel_task_failure_penalty", "status": "planned"},
    },
    {
        "catalog_key": "indulgence_day_card",
        "title": "放纵日卡",
        "description": "规划中的道具：未来用于开启当天失败减罚或免罚状态。",
        "category": "utility_item",
        "item_kind": "indulgence_day_card",
        "rarity": "epic",
        "source": "system",
        "price_tier": "medium",
        "price_secondary": 350,
        "inventory": None,
        "is_enabled": False,
        "is_stackable": True,
        "effect_payload": {"effect": "indulgence_day", "status": "planned"},
    },
    {
        "catalog_key": "wish_light_relax",
        "title": "轻度放松奖励",
        "description": "轻量现实奖励入口，例如一杯饮品、半小时娱乐时间或一次短休息。",
        "category": "wish_reward",
        "item_kind": "wish",
        "rarity": "common",
        "source": "system",
        "price_tier": "small",
        "price_secondary": 80,
        "inventory": None,
        "is_enabled": True,
        "is_stackable": True,
        "effect_payload": {},
    },
    {
        "catalog_key": "wish_weekend_entertainment",
        "title": "周末娱乐奖励",
        "description": "中等现实奖励入口，例如一场电影、一顿外食或一段较完整的娱乐时间。",
        "category": "wish_reward",
        "item_kind": "wish",
        "rarity": "rare",
        "source": "system",
        "price_tier": "medium",
        "price_secondary": 240,
        "inventory": None,
        "is_enabled": True,
        "is_stackable": True,
        "effect_payload": {},
    },
]


def seed_default_shop_items(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])
    WishItem = apps.get_model("shop", "WishItem")
    for user in User.objects.all():
        for payload in DEFAULT_SHOP_ITEMS:
            WishItem.objects.get_or_create(
                owner=user,
                catalog_key=payload["catalog_key"],
                defaults=payload,
            )


def remove_default_shop_items(apps, schema_editor):
    WishItem = apps.get_model("shop", "WishItem")
    WishItem.objects.filter(catalog_key__in=[item["catalog_key"] for item in DEFAULT_SHOP_ITEMS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0005_wishitem_catalog_key"),
    ]

    operations = [
        migrations.RunPython(seed_default_shop_items, remove_default_shop_items),
    ]
