from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel


class RewardTier(models.TextChoices):
    COMMON = "common", "普通"
    RARE = "rare", "优秀"
    EPIC = "epic", "暴击"
    LEGENDARY = "legendary", "传说"


class PityTier(models.TextChoices):
    NONE = "", "无"
    RARE = "rare", "优秀保底"
    EPIC = "epic", "暴击保底"
    LEGENDARY = "legendary", "传说保底"


class GachaPool(TimeStampedModel):
    name = models.CharField(max_length=80, verbose_name="卡池名称")
    cost_primary = models.PositiveIntegerField(default=50, verbose_name="抽卡消耗一级货币")
    common_reward = models.PositiveIntegerField(default=5, verbose_name="普通档奖励")
    rare_reward = models.PositiveIntegerField(default=20, verbose_name="优秀档奖励")
    epic_reward = models.PositiveIntegerField(default=40, verbose_name="暴击档奖励")
    legendary_reward = models.PositiveIntegerField(default=200, verbose_name="传说档奖励")
    common_rate = models.FloatField(default=0.72, verbose_name="普通档概率")
    rare_rate = models.FloatField(default=0.20, verbose_name="优秀档概率")
    epic_rate = models.FloatField(default=0.06, verbose_name="暴击档概率")
    legendary_rate = models.FloatField(default=0.02, verbose_name="传说档概率")
    rare_pity_threshold = models.PositiveIntegerField(default=10, verbose_name="优秀保底阈值")
    epic_pity_threshold = models.PositiveIntegerField(default=30, verbose_name="暴击保底阈值")
    legendary_pity_threshold = models.PositiveIntegerField(default=80, verbose_name="传说保底阈值")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        verbose_name = "卡池"
        verbose_name_plural = "卡池"

    def clean(self):
        super().clean()
        rates = {
            "common_rate": self.common_rate,
            "rare_rate": self.rare_rate,
            "epic_rate": self.epic_rate,
            "legendary_rate": self.legendary_rate,
        }
        errors = {}
        for field, value in rates.items():
            if value < 0 or value > 1:
                errors[field] = "概率必须在 0 到 1 之间。"

        total_rate = sum(rates.values())
        if abs(total_rate - 1.0) > 1e-9:
            errors["common_rate"] = "四档概率总和必须等于 1。"

        if self.rare_pity_threshold < 1:
            errors["rare_pity_threshold"] = "优秀保底阈值必须大于等于 1。"
        if self.epic_pity_threshold < 1:
            errors["epic_pity_threshold"] = "暴击保底阈值必须大于等于 1。"
        if self.legendary_pity_threshold < 1:
            errors["legendary_pity_threshold"] = "传说保底阈值必须大于等于 1。"
        if not (self.rare_pity_threshold < self.epic_pity_threshold < self.legendary_pity_threshold):
            errors["rare_pity_threshold"] = "保底阈值必须满足 rare < epic < legendary。"

        if errors:
            raise ValidationError(errors)


class GachaPoolUserState(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="gacha_pool_states")
    pool = models.ForeignKey(GachaPool, on_delete=models.CASCADE, related_name="user_states")
    total_draws = models.PositiveIntegerField(default=0, verbose_name="累计抽卡次数")
    draws_since_rare = models.PositiveIntegerField(default=0, verbose_name="距上次优秀及以上次数")
    draws_since_epic = models.PositiveIntegerField(default=0, verbose_name="距上次暴击及以上次数")
    draws_since_legendary = models.PositiveIntegerField(default=0, verbose_name="距上次传说次数")

    class Meta:
        verbose_name = "用户卡池状态"
        verbose_name_plural = "用户卡池状态"
        unique_together = ("owner", "pool")


class GachaDrawRecord(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="gacha_records")
    pool = models.ForeignKey(GachaPool, on_delete=models.PROTECT, related_name="draw_records")
    cost_primary = models.PositiveIntegerField(verbose_name="消耗一级货币")
    reward_secondary = models.PositiveIntegerField(verbose_name="获得二级货币")
    reward_tier = models.CharField(
        max_length=16,
        choices=RewardTier.choices,
        default=RewardTier.COMMON,
        verbose_name="奖励档位",
    )
    pity_tier = models.CharField(
        max_length=16,
        choices=PityTier.choices,
        blank=True,
        default=PityTier.NONE,
        verbose_name="触发的保底层级",
    )
    cost_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reward_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "抽卡记录"
        verbose_name_plural = "抽卡记录"
        ordering = ("-created_at", "-id")
