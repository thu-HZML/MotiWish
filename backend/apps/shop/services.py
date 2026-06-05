from django.db import models, transaction
from django.utils import timezone

from apps.shop.catalog import DEFAULT_SHOP_ITEMS
from apps.shop.models import (
    RedemptionRecord,
    RedemptionStatus,
    ShopItemCategory,
    UserInventory,
    WishItem,
    WishPriceTier,
    UserActiveEffect, 
)
from apps.users.services import grant_experience
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import reset_primary_debt, change_balance

PRICE_BOUNDS = {
    WishPriceTier.SMALL: {"min": 30, "max": 120},
    WishPriceTier.MEDIUM: {"min": 120, "max": 350},
    WishPriceTier.LARGE: {"min": 350, "max": 1200},
}


def clamp_price_by_tier(*, price_tier, suggested_price):
    bounds = PRICE_BOUNDS[price_tier]
    return max(bounds["min"], min(bounds["max"], suggested_price))


@transaction.atomic
def ensure_default_shop_items():
    # 默认商品 owner 设为 None，作为全局公共模板，避免对每个用户进行重复克隆
    created_items = []
    for payload in DEFAULT_SHOP_ITEMS:
        catalog_key = payload["catalog_key"]
        item, created = WishItem.objects.get_or_create(
            owner=None,
            catalog_key=catalog_key,
            defaults=payload,
        )
        if created:
            created_items.append(item)
    return created_items


def _decrease_stock(item):
    if item.inventory is not None:
        if item.inventory <= 0:
            raise ValueError("库存不足")
        item.inventory -= 1
        item.save(update_fields=["inventory", "updated_at"])


def _increase_inventory(*, user, item, quantity=1):
    inventory, _ = UserInventory.objects.select_for_update().get_or_create(
        owner=user,
        item=item,
        defaults={"quantity": 0},
    )
    if not item.is_stackable and inventory.quantity > 0:
        raise ValueError("该商品不可重复持有")
    inventory.quantity += quantity
    inventory.save(update_fields=["quantity", "updated_at"])
    return inventory


@transaction.atomic
def redeem_item(*, user, item):
    item = WishItem.objects.select_for_update().get(pk=item.pk)
    if not item.is_enabled:
        raise ValueError("该商品未上架")

    _decrease_stock(item)
    _, transaction_record = change_balance(
        user=user,
        currency_type=CurrencyType.SECONDARY,
        delta=-item.price_secondary,
        reason=TransactionReason.SHOP_REDEEM,
        reference_type="shop_item",
        reference_id=item.id,
        memo=f"购买商品：{item.title}",
    )

    status = RedemptionStatus.REQUESTED
    fulfilled_at = None
    effect_snapshot = {}

    # 根据合并后的单个 category 字段分发行为
    if item.category == ShopItemCategory.EXPERIENCE_PACK:
        experience = int(item.effect_payload.get("experience", 0))
        if experience <= 0:
            raise ValueError("经验材料必须配置正数 experience")
        effect_snapshot = grant_experience(user=user, amount=experience)
        status = RedemptionStatus.COMPLETED
        fulfilled_at = timezone.now()
    elif item.category in {
        ShopItemCategory.DEBT_REPAYMENT_CARD,
        ShopItemCategory.TASK_FAILURE_PROTECTION_CARD,
        ShopItemCategory.INDULGENCE_DAY_CARD,
    }:
        inventory = _increase_inventory(user=user, item=item)
        effect_snapshot = {"inventory_id": inventory.id, "quantity": inventory.quantity}
        status = RedemptionStatus.COMPLETED
        fulfilled_at = timezone.now()

    return RedemptionRecord.objects.create(
        owner=user,
        item=item,
        cost_secondary=item.price_secondary,
        status=status,
        transaction=transaction_record,
        effect_snapshot=effect_snapshot,
        fulfilled_at=fulfilled_at,
    )

@transaction.atomic
def use_inventory_item(*, user, inventory):
    inventory = UserInventory.objects.select_for_update().select_related("item").get(pk=inventory.pk, owner=user)
    if inventory.quantity <= 0:
        raise ValueError("道具数量不足")

    item = inventory.item
    
    # 限制：只有“还债卡”和“放纵日卡”允许用户主动点击使用
    if item.category not in {ShopItemCategory.DEBT_REPAYMENT_CARD, ShopItemCategory.INDULGENCE_DAY_CARD}:
        raise ValueError("该道具不能主动使用，属于被动或规划中道具")

    # 1. 还债卡的主动使用逻辑
    if item.category == ShopItemCategory.DEBT_REPAYMENT_CARD:
        wallet, transaction_record = reset_primary_debt(user=user, memo=f"使用道具：{item.title}")
        if transaction_record is None:
            raise ValueError("当前没有一级货币负债，不能使用还债卡")
        inventory.quantity -= 1
        inventory.save(update_fields=["quantity", "updated_at"])
        return {
            "inventory": inventory,
            "wallet": wallet,
            "transaction": transaction_record,
            "effect": "debt_reset",
        }

    # 2. 放纵日卡的主动使用逻辑（新实现）
    elif item.category == ShopItemCategory.INDULGENCE_DAY_CARD:
        now = timezone.now()
        
        # 检查今天是否已经是激活状态，防止重复使用浪费
        has_active = UserActiveEffect.objects.filter(
            owner=user,
            effect_type="indulgence_day",
            starts_at__lte=now,
            expires_at__gte=now,
        ).exists()
        if has_active:
            raise ValueError("今天已经是放纵日了，无需重复激活")

        # 计算当天的结束时刻 23:59:59 (符合“当天”有效的设计)
        from datetime import datetime, time
        today_end = timezone.make_aware(datetime.combine(timezone.localdate(), time.max))

        # 创建一个持续至当天结束的 Buff 效果
        effect_record = UserActiveEffect.objects.create(
            owner=user,
            effect_type="indulgence_day",
            source_item=item,
            starts_at=now,
            expires_at=today_end,
            remaining_uses=-1,
            effect_payload={"effect": "indulgence_day"}
        )
        
        inventory.quantity -= 1
        inventory.save(update_fields=["quantity", "updated_at"])
        return {
            "inventory": inventory,
            "effect_record": effect_record,
            "effect": "indulgence_day_activated",
        }

@transaction.atomic
def check_and_apply_failure_protection(*, user):
    """
    当用户发生任务失败、需要执行扣罚结算时，其他任务模块在底层扣款前应当调用该方法。
    
    优先级校验：
    1. 优先校验当前用户是否有激活中的“放纵日”Buff。若有，则直接豁免惩罚（不消耗任何保护卡）。
    2. 若无放纵日，则检查背包是否有“任务失败保护卡”。若有，自动被动扣除1张保护卡，豁免本次惩罚。
    
    返回：
        protected (bool): 是否触发惩罚豁免。如果为 True，业务层应跳过惩罚逻辑。
        protection_type (str/None): 触发保护的来源 ('indulgence_day' / 'protection_card' / None)
    """
    now = timezone.now()

    # 阶段 1：校验放纵日 Buff 状态
    has_indulgence = UserActiveEffect.objects.filter(
        owner=user,
        effect_type="indigo_day_card" if not hasattr(ShopItemCategory, "INDULGENCE_DAY_CARD") else "indulgence_day",
        starts_at__lte=now,
        expires_at__gte=now,
    ).exists()
    if has_indulgence:
        return True, "indulgence_day"

    # 阶段 2：校验并自动被动消耗“任务失败保护卡”
    protection_inventory = UserInventory.objects.select_for_update().filter(
        owner=user,
        item__category=ShopItemCategory.TASK_FAILURE_PROTECTION_CARD,
        quantity__gt=0
    ).first()

    if protection_inventory:
        protection_inventory.quantity -= 1
        protection_inventory.save(update_fields=["quantity", "updated_at"])
        return True, "protection_card"

    return False, None

@transaction.atomic
def fulfill_redemption(*, record, note=""):
    record = RedemptionRecord.objects.select_for_update().select_related("item").get(pk=record.pk)
    if record.status != RedemptionStatus.REQUESTED:
        raise ValueError("只有待处理的兑换记录才能兑现")
    record.status = RedemptionStatus.FULFILLED
    record.fulfilled_at = timezone.now()
    if note:
        record.note = note
    record.save(update_fields=["status", "fulfilled_at", "note", "updated_at"])
    return record


@transaction.atomic
def reject_redemption(*, record, note="", refund=None):
    record = RedemptionRecord.objects.select_for_update().select_related("item").get(pk=record.pk)
    if record.status != RedemptionStatus.REQUESTED:
        raise ValueError("只有待处理的兑换记录才能拒绝")

    should_refund = record.item.auto_refund_on_reject if refund is None else refund
    refund_transaction = None

    if should_refund:
        _, refund_transaction = change_balance(
            user=record.owner,
            currency_type=CurrencyType.SECONDARY,
            delta=record.cost_secondary,
            reason=TransactionReason.SHOP_REFUND,
            reference_type="redemption_record",
            reference_id=record.id,
            memo=f"兑换被拒退款：{record.item.title}",
        )
        if record.item.inventory is not None:
            record.item.inventory += 1
            record.item.save(update_fields=["inventory", "updated_at"])

    record.status = RedemptionStatus.REJECTED
    record.rejected_at = timezone.now()
    record.refund_transaction = refund_transaction
    if note:
        record.note = note
    record.save(update_fields=["status", "rejected_at", "refund_transaction", "note", "updated_at"])
    return record
