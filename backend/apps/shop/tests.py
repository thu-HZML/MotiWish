from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.shop.catalog import DEFAULT_SHOP_ITEMS
from apps.shop.models import RedemptionStatus, ShopItemCategory, UserInventory, WishItem, WishPriceTier
from apps.shop.services import (
    clamp_price_by_tier,
    ensure_default_shop_items,
    fulfill_redemption,
    redeem_item,
    reject_redemption,
    use_inventory_item,
)
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
        self.wish_item = WishItem.objects.create(
            owner=self.user,
            title="看一场电影",
            category=ShopItemCategory.WISH,
            price_tier=WishPriceTier.MEDIUM,
            price_secondary=180,
            inventory=1,
        )

    def test_clamp_price_by_tier(self):
        self.assertEqual(clamp_price_by_tier(price_tier=WishPriceTier.SMALL, suggested_price=10), 30)
        self.assertEqual(clamp_price_by_tier(price_tier=WishPriceTier.MEDIUM, suggested_price=200), 200)
        self.assertEqual(clamp_price_by_tier(price_tier=WishPriceTier.LARGE, suggested_price=1500), 1200)

    def test_ensure_default_shop_items_creates_public_catalog_once(self):
        created = ensure_default_shop_items()
        created_again = ensure_default_shop_items()

        self.assertEqual(len(created), len(DEFAULT_SHOP_ITEMS))
        self.assertEqual(len(created_again), 0)
        self.assertTrue(WishItem.objects.filter(owner=None, catalog_key="debt_repayment_card_standard").exists())
        self.assertFalse(WishItem.objects.get(owner=None, catalog_key="task_failure_protection_card").is_enabled)

    def test_redeem_wish_item_creates_requested_record(self):
        record = redeem_item(user=self.user, item=self.wish_item)
        self.wish_item.refresh_from_db()

        self.assertEqual(record.status, RedemptionStatus.REQUESTED)
        self.assertEqual(record.cost_secondary, 180)
        self.assertEqual(self.wish_item.inventory, 0)

    def test_redeem_experience_pack_grants_experience_immediately(self):
        item = WishItem.objects.create(
            owner=self.user,
            title="小份经验书",
            category=ShopItemCategory.EXPERIENCE_PACK,
            price_tier=WishPriceTier.SMALL,
            price_secondary=40,
            effect_payload={"experience": 120},
        )

        record = redeem_item(user=self.user, item=item)
        self.user.refresh_from_db()

        self.assertEqual(record.status, RedemptionStatus.COMPLETED)
        self.assertEqual(self.user.level, 2)
        self.assertEqual(self.user.experience, 20)
        self.assertEqual(self.user.total_experience, 120)

    def test_redeem_and_use_debt_repayment_card(self):
        change_balance(
            user=self.user,
            currency_type=CurrencyType.PRIMARY,
            delta=-60,
            reason=TransactionReason.TASK_PENALTY,
        )
        item = WishItem.objects.create(
            owner=self.user,
            title="还债卡",
            category=ShopItemCategory.DEBT_REPAYMENT_CARD,
            price_tier=WishPriceTier.MEDIUM,
            price_secondary=180,
        )

        record = redeem_item(user=self.user, item=item)
        inventory = UserInventory.objects.get(owner=self.user, item=item)
        result = use_inventory_item(user=self.user, inventory=inventory)

        self.assertEqual(record.status, RedemptionStatus.COMPLETED)
        self.assertEqual(result["wallet"].primary_balance, 0)
        self.assertEqual(result["inventory"].quantity, 0)

    def test_debt_repayment_card_requires_existing_debt(self):
        item = WishItem.objects.create(
            owner=self.user,
            title="还债卡",
            category=ShopItemCategory.DEBT_REPAYMENT_CARD,
            price_tier=WishPriceTier.MEDIUM,
            price_secondary=180,
        )

        redeem_item(user=self.user, item=item)
        inventory = UserInventory.objects.get(owner=self.user, item=item)

        with self.assertRaises(ValueError):
            use_inventory_item(user=self.user, inventory=inventory)
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 1)

    def test_fulfill_redemption_marks_record_done(self):
        record = redeem_item(user=self.user, item=self.wish_item)
        record = fulfill_redemption(record=record, note="已兑现")

        self.assertEqual(record.status, RedemptionStatus.FULFILLED)
        self.assertEqual(record.note, "已兑现")
        self.assertIsNotNone(record.fulfilled_at)

    def test_reject_redemption_refunds_and_restores_inventory(self):
        record = redeem_item(user=self.user, item=self.wish_item)
        record = reject_redemption(record=record, note="暂不满足条件", refund=True)
        self.wish_item.refresh_from_db()

        self.assertEqual(record.status, RedemptionStatus.REJECTED)
        self.assertIsNotNone(record.refund_transaction_id)
        self.assertEqual(self.wish_item.inventory, 1)
        self.assertEqual(
            WalletTransaction.objects.filter(owner=self.user, reason=TransactionReason.SHOP_REFUND).count(),
            1,
        )


class ShopItemApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="shop_api_user",
            email="shop-api@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_returns_public_items_and_hides_legacy_default_clones(self):
        WishItem.objects.create(
            owner=self.user,
            catalog_key="exp_pack_small",
            title="旧版用户默认商品",
            category=ShopItemCategory.EXPERIENCE_PACK,
            price_tier=WishPriceTier.SMALL,
            price_secondary=40,
        )
        WishItem.objects.create(
            owner=self.user,
            title="用户自定义愿望",
            category=ShopItemCategory.WISH,
            price_tier=WishPriceTier.SMALL,
            price_secondary=60,
        )

        response = self.client.get(reverse("wish-item-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 7)
        self.assertEqual(WishItem.objects.filter(owner=None).count(), len(DEFAULT_SHOP_ITEMS))
        titles = [item["title"] for item in response.data["data"]["results"]]
        self.assertIn("用户自定义愿望", titles)
        self.assertNotIn("旧版用户默认商品", titles)

    def test_create_custom_wish_item_is_private_to_owner(self):
        response = self.client.post(
            reverse("wish-item-list"),
            {
                "title": "Travel reward",
                "description": "A self-defined trip reward.",
                "price_tier": WishPriceTier.LARGE,
                "price_secondary": 800,
                "rarity": "epic",
                "inventory": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        item = WishItem.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(item.owner, self.user)
        self.assertEqual(item.category, ShopItemCategory.WISH)
        self.assertEqual(item.catalog_key, "")
        self.assertTrue(item.is_enabled)

        list_response = self.client.get(reverse("wish-item-list"), {"category": "wish_reward"})
        titles = [entry["title"] for entry in list_response.data["data"]["results"]]
        self.assertIn("Travel reward", titles)

        other_user = get_user_model().objects.create_user(
            username="other_shop_user",
            email="other-shop@example.com",
            password="Password123!",
        )
        self.client.force_authenticate(other_user)
        other_response = self.client.get(reverse("wish-item-list"), {"category": "wish_reward"})
        other_titles = [entry["title"] for entry in other_response.data["data"]["results"]]
        self.assertNotIn("Travel reward", other_titles)

    def test_user_can_update_and_delete_only_own_custom_wish_item(self):
        own_item = WishItem.objects.create(
            owner=self.user,
            title="Custom dinner reward",
            category=ShopItemCategory.WISH,
            price_tier=WishPriceTier.MEDIUM,
            price_secondary=180,
        )
        public_item = WishItem.objects.create(
            owner=None,
            catalog_key="public_wish_for_test",
            title="Public wish reward",
            category=ShopItemCategory.WISH,
            price_tier=WishPriceTier.MEDIUM,
            price_secondary=200,
        )

        patch_response = self.client.patch(
            reverse("wish-item-detail", kwargs={"pk": own_item.pk}),
            {"price_secondary": 220},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        own_item.refresh_from_db()
        self.assertEqual(own_item.price_secondary, 220)

        public_patch_response = self.client.patch(
            reverse("wish-item-detail", kwargs={"pk": public_item.pk}),
            {"price_secondary": 220},
            format="json",
        )
        self.assertEqual(public_patch_response.status_code, 404)

        delete_response = self.client.delete(reverse("wish-item-detail", kwargs={"pk": own_item.pk}))
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(WishItem.objects.filter(pk=own_item.pk).exists())

