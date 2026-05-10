from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.users.models import DynamicProfile, StableProfile, User


class UserProfileStatusTests(TestCase):
    def test_basic_profile_status_updates_from_user_fields(self):
        user = User.objects.create_user(
            username="profile_user",
            email="profile@example.com",
            password="Password123!",
        )

        self.assertFalse(user.basic_profile_completed)
        self.assertIn("nickname", user.basic_profile_missing_fields)
        self.assertIn("long_term_goals", user.basic_profile_missing_fields)

        user.nickname = "时间炼金师"
        user.gender = User.Gender.MALE
        user.occupation = User.Occupation.STUDENT
        user.education_stage = User.EducationStage.COLLEGE
        user.language_preference = User.LanguagePreference.ZH_HANS
        user.timezone = "Asia/Shanghai"
        user.long_term_goals = [User.GoalCategory.LEARNING]
        user.focus_areas = [User.FocusArea.EXAM]
        user.save()

        self.assertTrue(user.basic_profile_completed)
        self.assertEqual(user.basic_profile_completion_score, 100)
        self.assertEqual(user.basic_profile_missing_fields, [])

    def test_stable_profile_prompt_logic_uses_interval(self):
        user = User.objects.create_user(
            username="stable_user",
            email="stable@example.com",
            password="Password123!",
        )
        profile = StableProfile.objects.create(user=user)

        self.assertTrue(profile.should_prompt)
        profile.last_prompted_at = timezone.now()
        profile.save()
        self.assertFalse(profile.should_prompt)

        profile.last_prompted_at = timezone.now() - timedelta(days=StableProfile.PROMPT_INTERVAL_DAYS, minutes=1)
        profile.save()
        self.assertTrue(profile.should_prompt)

    def test_dynamic_profile_reports_meaningful_data(self):
        user = User.objects.create_user(
            username="dynamic_user",
            email="dynamic@example.com",
            password="Password123!",
        )
        profile = DynamicProfile.objects.create(user=user)
        self.assertFalse(profile.has_meaningful_data)

        profile.current_top_goal = "完成期末复习计划"
        profile.save()
        self.assertTrue(profile.has_meaningful_data)
