from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.shop.models import RedemptionStatus, WishItem, WishPriceTier
from apps.shop.services import clamp_price_by_tier, fulfill_redemption, redeem_item, reject_redemption
from apps.wallet.models import CurrencyType, TransactionReason, WalletTransaction
from apps.wallet.services import change_balance


class ShopServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="shop_user",
            email="shop@example.com",
            password="Password123!",
        )
        change_balance(
            user=self.user,
            currency_type=CurrencyType.SECONDARY,
            delta=500,
            reason=TransactionReason.MANUAL_ADJUST,
        )
        self.item = WishItem.objects.create(
            owner=self.user,
            title="看一场电影",
            price_tier=WishPriceTier.MEDIUM,
            price_secondary=180,
            inventory=1,
        )

    def test_clamp_price_by_tier(self):
        self.assertEqual(clamp_price_by_tier(price_tier=WishPriceTier.SMALL, suggested_price=10), 30)
        self.assertEqual(clamp_price_by_tier(price_tier=WishPriceTier.MEDIUM, suggested_price=200), 200)
        self.assertEqual(clamp_price_by_tier(price_tier=WishPriceTier.LARGE, suggested_price=1500), 1200)

    def test_redeem_item_creates_requested_record(self):
        record = redeem_item(user=self.user, item=self.item)
        self.item.refresh_from_db()

        self.assertEqual(record.status, RedemptionStatus.REQUESTED)
        self.assertEqual(record.cost_secondary, 180)
        self.assertEqual(self.item.inventory, 0)

    def test_fulfill_redemption_marks_record_done(self):
        record = redeem_item(user=self.user, item=self.item)
        record = fulfill_redemption(record=record, note="已兑现")

        self.assertEqual(record.status, RedemptionStatus.FULFILLED)
        self.assertEqual(record.note, "已兑现")
        self.assertIsNotNone(record.fulfilled_at)

    def test_reject_redemption_refunds_and_restores_inventory(self):
        record = redeem_item(user=self.user, item=self.item)
        record = reject_redemption(record=record, note="暂不满足条件", refund=True)
        self.item.refresh_from_db()

        self.assertEqual(record.status, RedemptionStatus.REJECTED)
        self.assertIsNotNone(record.refund_transaction_id)
        self.assertEqual(self.item.inventory, 1)
        self.assertEqual(
            WalletTransaction.objects.filter(owner=self.user, reason=TransactionReason.SHOP_REFUND).count(),
            1,
        )
