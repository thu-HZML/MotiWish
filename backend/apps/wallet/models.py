from django.db import models

from apps.common.models import TimeStampedModel


class CurrencyType(models.TextChoices):
    PRIMARY = "primary", "一级货币"
    SECONDARY = "secondary", "二级货币"


class TransactionReason(models.TextChoices):
    TASK_REWARD = "task_reward", "任务奖励"
    TASK_PENALTY = "task_penalty", "任务惩罚"
    GACHA_COST = "gacha_cost", "抽卡消耗"
    GACHA_REWARD = "gacha_reward", "抽卡奖励"
    SHOP_REDEEM = "shop_redeem", "商店兑换"
    MANUAL_ADJUST = "manual_adjust", "后台调整"


class Wallet(TimeStampedModel):
    owner = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="wallet")
    primary_balance = models.PositiveIntegerField(default=0, verbose_name="一级货币余额")
    secondary_balance = models.PositiveIntegerField(default=0, verbose_name="二级货币余额")

    class Meta:
        verbose_name = "钱包"
        verbose_name_plural = "钱包"


class WalletTransaction(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="wallet_transactions")
    wallet = models.ForeignKey("wallet.Wallet", on_delete=models.CASCADE, related_name="transactions")
    currency_type = models.CharField(max_length=20, choices=CurrencyType.choices, verbose_name="货币类型")
    reason = models.CharField(max_length=32, choices=TransactionReason.choices, verbose_name="交易原因")
    delta = models.IntegerField(verbose_name="变动值")
    balance_before = models.PositiveIntegerField(verbose_name="变更前余额")
    balance_after = models.PositiveIntegerField(verbose_name="变更后余额")
    reference_type = models.CharField(max_length=50, blank=True, verbose_name="引用对象类型")
    reference_id = models.CharField(max_length=50, blank=True, verbose_name="引用对象ID")
    memo = models.CharField(max_length=255, blank=True, verbose_name="备注")
    payload = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")

    class Meta:
        verbose_name = "钱包流水"
        verbose_name_plural = "钱包流水"
        ordering = ("-created_at", "-id")
