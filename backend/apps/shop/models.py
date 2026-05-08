from django.db import models

from apps.common.models import TimeStampedModel, UserOwnedModel


class WishSource(models.TextChoices):
    MANUAL = "manual", "用户创建"
    SYSTEM = "system", "系统推荐"


class WishPriceTier(models.TextChoices):
    SMALL = "small", "小愿望"
    MEDIUM = "medium", "中愿望"
    LARGE = "large", "大愿望"


class RedemptionStatus(models.TextChoices):
    REQUESTED = "requested", "待处理"
    FULFILLED = "fulfilled", "已兑现"
    REJECTED = "rejected", "已拒绝"


class WishItem(UserOwnedModel):
    title = models.CharField(max_length=120, verbose_name="愿望名称")
    description = models.TextField(blank=True, verbose_name="愿望描述")
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
    auto_refund_on_reject = models.BooleanField(default=True, verbose_name="拒绝时自动退款")
    ai_pricing = models.JSONField(default=dict, blank=True, verbose_name="AI 定价数据")

    class Meta:
        verbose_name = "愿望商品"
        verbose_name_plural = "愿望商品"
        ordering = ("-created_at", "-id")


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
    fulfilled_at = models.DateTimeField(null=True, blank=True, verbose_name="兑现时间")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="拒绝时间")

    class Meta:
        verbose_name = "兑换记录"
        verbose_name_plural = "兑换记录"
        ordering = ("-created_at", "-id")
