from django.db import transaction

from apps.wallet.models import CurrencyType, TransactionReason, Wallet, WalletTransaction


class InsufficientBalanceError(ValueError):
    pass


def _apply_balance_change(*, wallet, currency_type, delta):
    balance_field = "primary_balance" if currency_type == CurrencyType.PRIMARY else "secondary_balance"
    balance_before = getattr(wallet, balance_field)
    balance_after = balance_before + delta

    if currency_type == CurrencyType.PRIMARY:
        if balance_after < Wallet.PRIMARY_DEBT_FLOOR:
            raise InsufficientBalanceError(
                f"{currency_type} 余额不足，最低可透支到 {Wallet.PRIMARY_DEBT_FLOOR}"
            )
    elif balance_after < 0:
        raise InsufficientBalanceError(f"{currency_type} 余额不足")

    setattr(wallet, balance_field, balance_after)
    wallet.save(update_fields=[balance_field, "updated_at"])
    return balance_before, balance_after


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
    balance_before, balance_after = _apply_balance_change(
        wallet=wallet,
        currency_type=currency_type,
        delta=delta,
    )
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


@transaction.atomic
def reset_primary_debt(*, user, memo="触发债务重置"):
    wallet, _ = Wallet.objects.select_for_update().get_or_create(owner=user)
    if wallet.primary_balance >= 0:
        return wallet, None

    delta = abs(wallet.primary_balance)
    balance_before, balance_after = _apply_balance_change(
        wallet=wallet,
        currency_type=CurrencyType.PRIMARY,
        delta=delta,
    )
    transaction_record = WalletTransaction.objects.create(
        owner=user,
        wallet=wallet,
        currency_type=CurrencyType.PRIMARY,
        reason=TransactionReason.DEBT_RESET,
        delta=delta,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type="wallet",
        reference_id=str(wallet.id),
        memo=memo,
        payload={"reset": True},
    )
    return wallet, transaction_record
