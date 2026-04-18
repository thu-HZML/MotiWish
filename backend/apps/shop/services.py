from django.db import transaction

from apps.shop.models import RedemptionRecord, WishItem
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import change_balance


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
