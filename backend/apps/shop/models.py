from django.db import models

from apps.common.models import TimeStampedModel, UserOwnedModel


class WishSource(models.TextChoices):
    MANUAL = "manual", "用户创建"
    SYSTEM = "system", "系统推荐"


class WishPriceTier(models.TextChoices):
    SMALL = "small", "小型"
    MEDIUM = "medium", "中型"
    LARGE = "large", "大型"


class ShopItemCategory(models.TextChoices):
    GROWTH_MATERIAL = "growth_material", "养成材料"
    UTILITY_ITEM = "utility_item", "功能轻道具"
    WISH_REWARD = "wish_reward", "愿望奖励"


class ShopItemKind(models.TextChoices):
    EXPERIENCE_PACK = "experience_pack", "经验材料"
    DEBT_REPAYMENT_CARD = "debt_repayment_card", "还债卡"
    TASK_FAILURE_PROTECTION_CARD = "task_failure_protection_card", "任务失败保护卡"
    INDULGENCE_DAY_CARD = "indulgence_day_card", "放纵日卡"
    WISH = "wish", "愿望"


class ShopItemRarity(models.TextChoices):
    COMMON = "common", "普通"
    RARE = "rare", "稀有"
    EPIC = "epic", "珍贵"


class RedemptionStatus(models.TextChoices):
    REQUESTED = "requested", "待处理"
    COMPLETED = "completed", "已完成"
    FULFILLED = "fulfilled", "已兑现"
    REJECTED = "rejected", "已拒绝"


class WishItem(UserOwnedModel):
    catalog_key = models.CharField(max_length=64, blank=True, db_index=True, verbose_name="目录键")
    title = models.CharField(max_length=120, verbose_name="商品名称")
    description = models.TextField(blank=True, verbose_name="商品描述")
    category = models.CharField(
        max_length=32,
        choices=ShopItemCategory.choices,
        default=ShopItemCategory.WISH_REWARD,
        verbose_name="商品大类",
    )
    item_kind = models.CharField(
        max_length=40,
        choices=ShopItemKind.choices,
        default=ShopItemKind.WISH,
        verbose_name="商品类型",
    )
    rarity = models.CharField(
        max_length=16,
        choices=ShopItemRarity.choices,
        default=ShopItemRarity.COMMON,
        verbose_name="稀有度",
    )
    source = models.CharField(max_length=20, choices=WishSource.choices, default=WishSource.MANUAL)
    price_tier = models.CharField(
        max_length=16,
        choices=WishPriceTier.choices,
        default=WishPriceTier.MEDIUM,
        verbose_name="价格档位",
    )
    price_secondary = models.PositiveIntegerField(verbose_name="二级货币定价")
    inventory = models.PositiveIntegerField(null=True, blank=True, verbose_name="库存")
    is_enabled = models.BooleanField(default=True, verbose_name="是否上架")
    is_stackable = models.BooleanField(default=True, verbose_name="是否可叠加持有")
    auto_refund_on_reject = models.BooleanField(default=True, verbose_name="拒绝时自动退款")
    ai_pricing = models.JSONField(default=dict, blank=True, verbose_name="AI 定价数据")
    effect_payload = models.JSONField(default=dict, blank=True, verbose_name="效果配置")

    class Meta:
        verbose_name = "商店商品"
        verbose_name_plural = "商店商品"
        ordering = ("-created_at", "-id")


class UserInventory(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="shop_inventory")
    item = models.ForeignKey(WishItem, on_delete=models.PROTECT, related_name="inventory_records")
    quantity = models.PositiveIntegerField(default=0, verbose_name="持有数量")

    class Meta:
        verbose_name = "用户道具库存"
        verbose_name_plural = "用户道具库存"
        unique_together = ("owner", "item")
        ordering = ("-updated_at", "-id")


class RedemptionRecord(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="redemption_records")
    item = models.ForeignKey(WishItem, on_delete=models.PROTECT, related_name="redemptions")
    cost_secondary = models.PositiveIntegerField(verbose_name="消耗二级货币")
    status = models.CharField(max_length=20, choices=RedemptionStatus.choices, default=RedemptionStatus.REQUESTED)
    note = models.CharField(max_length=255, blank=True, verbose_name="备注")
    transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    refund_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    effect_snapshot = models.JSONField(default=dict, blank=True, verbose_name="效果快照")
    fulfilled_at = models.DateTimeField(null=True, blank=True, verbose_name="兑现时间")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="拒绝时间")

    class Meta:
        verbose_name = "兑换记录"
        verbose_name_plural = "兑换记录"
        ordering = ("-created_at", "-id")
