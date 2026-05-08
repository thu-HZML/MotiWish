from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.wallet.models import CurrencyType, TransactionReason, Wallet
from apps.wallet.services import InsufficientBalanceError, change_balance, reset_primary_debt


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="wallet_user",
            email="wallet@example.com",
            password="Password123!",
        )

    def test_primary_balance_can_go_negative_until_floor(self):
        wallet, _ = change_balance(
            user=self.user,
            currency_type=CurrencyType.PRIMARY,
            delta=-60,
            reason=TransactionReason.MANUAL_ADJUST,
        )
        self.assertEqual(wallet.primary_balance, -60)
        self.assertTrue(wallet.is_in_debt)
        self.assertEqual(wallet.primary_debt, 60)

        wallet, _ = change_balance(
            user=self.user,
            currency_type=CurrencyType.PRIMARY,
            delta=-40,
            reason=TransactionReason.MANUAL_ADJUST,
        )
        self.assertEqual(wallet.primary_balance, Wallet.PRIMARY_DEBT_FLOOR)

    def test_primary_balance_cannot_go_below_floor(self):
        with self.assertRaises(InsufficientBalanceError):
            change_balance(
                user=self.user,
                currency_type=CurrencyType.PRIMARY,
                delta=Wallet.PRIMARY_DEBT_FLOOR - 1,
                reason=TransactionReason.MANUAL_ADJUST,
            )

    def test_secondary_balance_cannot_go_negative(self):
        with self.assertRaises(InsufficientBalanceError):
            change_balance(
                user=self.user,
                currency_type=CurrencyType.SECONDARY,
                delta=-1,
                reason=TransactionReason.SHOP_REDEEM,
            )

    def test_reset_primary_debt_sets_balance_to_zero(self):
        change_balance(
            user=self.user,
            currency_type=CurrencyType.PRIMARY,
            delta=-50,
            reason=TransactionReason.MANUAL_ADJUST,
        )
        wallet, transaction = reset_primary_debt(user=self.user)

        self.assertEqual(wallet.primary_balance, 0)
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.reason, TransactionReason.DEBT_RESET)
        self.assertEqual(transaction.delta, 50)
