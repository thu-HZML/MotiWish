import random

from django.db import transaction

from apps.gacha.models import GachaDrawRecord, GachaPoolUserState, PityTier, RewardTier
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import change_balance


def _resolve_reward(pool, state):
    if state.draws_since_legendary >= pool.legendary_pity_threshold:
        return RewardTier.LEGENDARY, pool.legendary_reward, PityTier.LEGENDARY
    if state.draws_since_epic >= pool.epic_pity_threshold:
        return RewardTier.EPIC, pool.epic_reward, PityTier.EPIC
    if state.draws_since_rare >= pool.rare_pity_threshold:
        return RewardTier.RARE, pool.rare_reward, PityTier.RARE

    roll = random.random()
    if roll < pool.legendary_rate:
        return RewardTier.LEGENDARY, pool.legendary_reward, PityTier.NONE
    if roll < pool.legendary_rate + pool.epic_rate:
        return RewardTier.EPIC, pool.epic_reward, PityTier.NONE
    if roll < pool.legendary_rate + pool.epic_rate + pool.rare_rate:
        return RewardTier.RARE, pool.rare_reward, PityTier.NONE
    return RewardTier.COMMON, pool.common_reward, PityTier.NONE


def _update_state_after_draw(state, reward_tier):
    state.total_draws += 1
    state.draws_since_rare += 1
    state.draws_since_epic += 1
    state.draws_since_legendary += 1

    if reward_tier in {RewardTier.RARE, RewardTier.EPIC, RewardTier.LEGENDARY}:
        state.draws_since_rare = 0
    if reward_tier in {RewardTier.EPIC, RewardTier.LEGENDARY}:
        state.draws_since_epic = 0
    if reward_tier == RewardTier.LEGENDARY:
        state.draws_since_legendary = 0

    state.save(
        update_fields=[
            "total_draws",
            "draws_since_rare",
            "draws_since_epic",
            "draws_since_legendary",
            "updated_at",
        ]
    )


@transaction.atomic
def draw_once(*, user, pool):
    state, _ = GachaPoolUserState.objects.select_for_update().get_or_create(
        owner=user,
        pool=pool,
    )
    reward_tier, reward_secondary, pity_tier = _resolve_reward(pool, state)
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
        payload={
            "reward_tier": reward_tier,
            "pity_tier": pity_tier or None,
        },
    )
    _update_state_after_draw(state, reward_tier)
    return GachaDrawRecord.objects.create(
        owner=user,
        pool=pool,
        cost_primary=pool.cost_primary,
        reward_secondary=reward_secondary,
        reward_tier=reward_tier,
        pity_tier=pity_tier,
        cost_transaction=cost_transaction,
        reward_transaction=reward_transaction,
    )
