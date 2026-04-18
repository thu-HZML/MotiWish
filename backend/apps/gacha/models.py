from django.db import models

from apps.common.models import TimeStampedModel


class GachaPool(TimeStampedModel):
    name = models.CharField(max_length=80, verbose_name="卡池名称")
    cost_primary = models.PositiveIntegerField(default=10, verbose_name="抽卡消耗")
    base_secondary_reward = models.PositiveIntegerField(default=5, verbose_name="基础二级货币")
    bonus_rate = models.FloatField(default=0.15, verbose_name="小暴击概率")
    jackpot_rate = models.FloatField(default=0.03, verbose_name="大暴击概率")
    bonus_multiplier = models.PositiveIntegerField(default=2, verbose_name="小暴击倍率")
    jackpot_multiplier = models.PositiveIntegerField(default=5, verbose_name="大暴击倍率")
    pity_threshold = models.PositiveIntegerField(default=10, verbose_name="保底阈值")
    pity_multiplier = models.PositiveIntegerField(default=3, verbose_name="保底倍率")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        verbose_name = "卡池"
        verbose_name_plural = "卡池"


class GachaDrawRecord(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="gacha_records")
    pool = models.ForeignKey(GachaPool, on_delete=models.PROTECT, related_name="draw_records")
    cost_primary = models.PositiveIntegerField(verbose_name="消耗一级货币")
    reward_secondary = models.PositiveIntegerField(verbose_name="获得二级货币")
    multiplier = models.PositiveIntegerField(verbose_name="命中倍率")
    is_bonus = models.BooleanField(default=False, verbose_name="是否小暴击")
    is_jackpot = models.BooleanField(default=False, verbose_name="是否大暴击")
    is_pity = models.BooleanField(default=False, verbose_name="是否保底")
    cost_transaction = models.ForeignKey("wallet.WalletTransaction", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reward_transaction = models.ForeignKey("wallet.WalletTransaction", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "抽卡记录"
        verbose_name_plural = "抽卡记录"
        ordering = ("-created_at", "-id")
