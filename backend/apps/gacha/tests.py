from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.gacha.models import GachaPool, GachaPoolUserState, PityTier, RewardTier
from apps.gacha.services import draw_once
from apps.wallet.models import CurrencyType, TransactionReason, WalletTransaction
from apps.wallet.services import change_balance


class GachaServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="gacha_user",
            email="gacha@example.com",
            password="Password123!",
        )
        self.pool = GachaPool.objects.create(name="标准池")
        change_balance(
            user=self.user,
            currency_type=CurrencyType.PRIMARY,
            delta=500,
            reason=TransactionReason.MANUAL_ADJUST,
        )

    @patch("apps.gacha.services.random.random", return_value=0.99)
    def test_common_draw_updates_state_and_wallet(self, _mock_random):
        record = draw_once(user=self.user, pool=self.pool)
        state = GachaPoolUserState.objects.get(owner=self.user, pool=self.pool)

        self.assertEqual(record.reward_tier, RewardTier.COMMON)
        self.assertEqual(record.reward_secondary, self.pool.common_reward)
        self.assertEqual(record.pity_tier, PityTier.NONE)
        self.assertEqual(state.total_draws, 1)
        self.assertEqual(state.draws_since_rare, 1)
        self.assertEqual(state.draws_since_epic, 1)
        self.assertEqual(state.draws_since_legendary, 1)

    @patch("apps.gacha.services.random.random", return_value=0.99)
    def test_rare_pity_triggers_after_threshold(self, _mock_random):
        state = GachaPoolUserState.objects.create(
            owner=self.user,
            pool=self.pool,
            draws_since_rare=self.pool.rare_pity_threshold,
            draws_since_epic=0,
            draws_since_legendary=0,
        )
        record = draw_once(user=self.user, pool=self.pool)
        state.refresh_from_db()

        self.assertEqual(record.reward_tier, RewardTier.RARE)
        self.assertEqual(record.pity_tier, PityTier.RARE)
        self.assertEqual(state.draws_since_rare, 0)
        self.assertEqual(state.draws_since_epic, 1)
        self.assertEqual(state.draws_since_legendary, 1)

    @patch("apps.gacha.services.random.random", return_value=0.0)
    def test_legendary_draw_resets_all_counters(self, _mock_random):
        state = GachaPoolUserState.objects.create(
            owner=self.user,
            pool=self.pool,
            draws_since_rare=5,
            draws_since_epic=10,
            draws_since_legendary=20,
        )
        record = draw_once(user=self.user, pool=self.pool)
        state.refresh_from_db()

        self.assertEqual(record.reward_tier, RewardTier.LEGENDARY)
        self.assertEqual(state.draws_since_rare, 0)
        self.assertEqual(state.draws_since_epic, 0)
        self.assertEqual(state.draws_since_legendary, 0)

    def test_draw_creates_wallet_transactions(self):
        with patch("apps.gacha.services.random.random", return_value=0.99):
            record = draw_once(user=self.user, pool=self.pool)

        self.assertIsNotNone(record.cost_transaction_id)
        self.assertIsNotNone(record.reward_transaction_id)
        self.assertEqual(
            WalletTransaction.objects.filter(owner=self.user, reason=TransactionReason.GACHA_COST).count(),
            1,
        )
        self.assertEqual(
            WalletTransaction.objects.filter(owner=self.user, reason=TransactionReason.GACHA_REWARD).count(),
            1,
        )
