from django.db import transaction
from django.utils import timezone

from apps.shop.models import RedemptionRecord, RedemptionStatus, WishItem, WishPriceTier
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import change_balance

PRICE_BOUNDS = {
    WishPriceTier.SMALL: {"min": 30, "max": 120},
    WishPriceTier.MEDIUM: {"min": 100, "max": 350},
    WishPriceTier.LARGE: {"min": 300, "max": 1200},
}


def clamp_price_by_tier(*, price_tier, suggested_price):
    bounds = PRICE_BOUNDS[price_tier]
    return max(bounds["min"], min(bounds["max"], suggested_price))


@transaction.atomic
def redeem_item(*, user, item):
    item = WishItem.objects.select_for_update().get(pk=item.pk)
    if not item.is_enabled:
        raise ValueError("该商品未上架")
    if item.inventory is not None and item.inventory <= 0:
        raise ValueError("库存不足")
    _, transaction_record = change_balance(
        user=user,
        currency_type=CurrencyType.SECONDARY,
        delta=-item.price_secondary,
        reason=TransactionReason.SHOP_REDEEM,
        reference_type="wish_item",
        reference_id=item.id,
        memo=f"兑换愿望：{item.title}",
    )
    if item.inventory is not None:
        item.inventory -= 1
        item.save(update_fields=["inventory", "updated_at"])
    return RedemptionRecord.objects.create(
        owner=user,
        item=item,
        cost_secondary=item.price_secondary,
        transaction=transaction_record,
    )


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
