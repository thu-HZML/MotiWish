import random

from django.db import transaction

from apps.gacha.models import GachaDrawRecord
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import change_balance


@transaction.atomic
def draw_once(*, user, pool):
    history_count = GachaDrawRecord.objects.select_for_update().filter(owner=user, pool=pool).count()
    is_pity = history_count > 0 and (history_count + 1) % pool.pity_threshold == 0
    is_jackpot = False
    is_bonus = False
    multiplier = 1
    if is_pity:
        multiplier = pool.pity_multiplier
    else:
        roll = random.random()
        if roll < pool.jackpot_rate:
            is_jackpot = True
            multiplier = pool.jackpot_multiplier
        elif roll < pool.jackpot_rate + pool.bonus_rate:
            is_bonus = True
            multiplier = pool.bonus_multiplier
    reward_secondary = pool.base_secondary_reward * multiplier
    _, cost_transaction = change_balance(
        user=user,
        currency_type=CurrencyType.PRIMARY,
        delta=-pool.cost_primary,
        reason=TransactionReason.GACHA_COST,
        reference_type="gacha_pool",
        reference_id=pool.id,
        memo=f"抽卡消耗：{pool.name}",
    )
    _, reward_transaction = change_balance(
        user=user,
        currency_type=CurrencyType.SECONDARY,
        delta=reward_secondary,
        reason=TransactionReason.GACHA_REWARD,
        reference_type="gacha_pool",
        reference_id=pool.id,
        memo=f"抽卡奖励：{pool.name}",
    )
    return GachaDrawRecord.objects.create(
        owner=user,
        pool=pool,
        cost_primary=pool.cost_primary,
        reward_secondary=reward_secondary,
        multiplier=multiplier,
        is_bonus=is_bonus,
        is_jackpot=is_jackpot,
        is_pity=is_pity,
        cost_transaction=cost_transaction,
        reward_transaction=reward_transaction,
    )
