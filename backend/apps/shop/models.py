from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel


class WishPriceTier(models.TextChoices):
    SMALL = "small", "小型"
    MEDIUM = "medium", "中型"
    LARGE = "large", "大型"


# 合并原 ShopItemCategory 与 ShopItemKind 为统一的 category
class ShopItemCategory(models.TextChoices):
    EXPERIENCE_PACK = "experience_pack", "经验材料"
    DEBT_REPAYMENT_CARD = "debt_repayment_card", "还债卡"
    TASK_FAILURE_PROTECTION_CARD = "task_failure_protection_card", "任务失败保护卡"
    INDULGENCE_DAY_CARD = "indulgence_day_card", "放纵日卡"
    WISH = "wish", "愿望奖励"


class ShopItemRarity(models.TextChoices):
    COMMON = "common", "普通"
    RARE = "rare", "稀有"
    EPIC = "epic", "珍贵"


class RedemptionStatus(models.TextChoices):
    REQUESTED = "requested", "待处理"
    COMPLETED = "completed", "已完成"
    FULFILLED = "fulfilled", "已兑现"
    REJECTED = "rejected", "已拒绝"


# 改为继承 TimeStampedModel，使 owner 可空
class WishItem(TimeStampedModel):
    owner = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="wish_items",
        verbose_name="所属用户",
    )
    catalog_key = models.CharField(max_length=64, blank=True, db_index=True, verbose_name="目录键")
    title = models.CharField(max_length=120, verbose_name="商品名称")
    description = models.TextField(blank=True, verbose_name="商品描述")
    category = models.CharField(
        max_length=40,
        choices=ShopItemCategory.choices,
        default=ShopItemCategory.WISH,
        verbose_name="商品分类",
    )
    rarity = models.CharField(
        max_length=16,
        choices=ShopItemRarity.choices,
        default=ShopItemRarity.COMMON,
        verbose_name="稀有度",
    )
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
    effect_payload = models.JSONField(default=dict, blank=True, verbose_name="效果配置")

    class Meta:
        verbose_name = "商店商品"
        verbose_name_plural = "商店商品"
        ordering = ("-created_at", "-id")

    def __str__(self):
        owner_info = f" [用户: {self.owner.username}]" if self.owner else " [系统公共]"
        return f"{self.title}{owner_info}"


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


class UserActiveEffect(TimeStampedModel):
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="active_effects",
        verbose_name="拥有者"
    )
    effect_type = models.CharField(max_length=50, verbose_name="效果类型")  # 例如 "indulgence_day"
    source_item = models.ForeignKey(
        "WishItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="来源道具"
    )
    starts_at = models.DateTimeField(verbose_name="开始时间")
    expires_at = models.DateTimeField(verbose_name="过期时间")
    remaining_uses = models.IntegerField(default=-1, verbose_name="剩余使用次数")  # -1代表根据时间自然过期，不受次数限制
    effect_payload = models.JSONField(default=dict, blank=True, verbose_name="效果附加负载")

    class Meta:
        verbose_name = "用户有效效果/Buff"
        verbose_name_plural = "用户有效效果/Buff"
        ordering = ("-created_at",)

    def is_active(self):
        now = timezone.now()
        return self.starts_at <= now <= self.expires_at and (self.remaining_uses == -1 or self.remaining_uses > 0)