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
)
from apps.users.services import grant_experience
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import reset_primary_debt, change_balance

PRICE_BOUNDS = {
    WishPriceTier.SMALL: {"min": 30, "max": 120},
    WishPriceTier.MEDIUM: {"min": 100, "max": 350},
    WishPriceTier.LARGE: {"min": 300, "max": 1200},
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
    if item.category != ShopItemCategory.DEBT_REPAYMENT_CARD:
        raise ValueError("该道具当前暂不支持主动使用")

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