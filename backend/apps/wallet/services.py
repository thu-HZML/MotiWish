from django.db import transaction

from apps.wallet.models import CurrencyType, Wallet, WalletTransaction


class InsufficientBalanceError(ValueError):
    pass


@transaction.atomic
def change_balance(
    *,
    user,
    currency_type,
    delta,
    reason,
    reference_type="",
    reference_id="",
    memo="",
    payload=None,
):
    wallet, _ = Wallet.objects.select_for_update().get_or_create(owner=user)
    payload = payload or {}
    balance_field = "primary_balance" if currency_type == CurrencyType.PRIMARY else "secondary_balance"
    balance_before = getattr(wallet, balance_field)
    balance_after = balance_before + delta
    if balance_after < 0:
        raise InsufficientBalanceError(f"{currency_type} 余额不足")
    setattr(wallet, balance_field, balance_after)
    wallet.save(update_fields=[balance_field, "updated_at"])
    transaction_record = WalletTransaction.objects.create(
        owner=user,
        wallet=wallet,
        currency_type=currency_type,
        reason=reason,
        delta=delta,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type=reference_type,
        reference_id=str(reference_id or ""),
        memo=memo,
        payload=payload,
    )
    return wallet, transaction_record
