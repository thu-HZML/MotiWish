from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.users.models import DynamicProfile, StableProfile, User


class RegisterApiTests(APITestCase):
    def test_register_requires_matching_password_confirm(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "register_mismatch",
                "email": "mismatch@example.com",
                "password": "StrongPass123!",
                "password_confirm": "DifferentPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")
        self.assertIn("password_confirm", response.data["data"])
        self.assertIn("两次输入的密码不一致。", response.data["data"]["password_confirm"])

    def test_register_returns_password_validator_messages(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "register_numeric",
                "email": "numeric@example.com",
                "password": "12345678",
                "password_confirm": "12345678",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("password", response.data["data"])
        password_errors = " ".join(str(item) for item in response.data["data"]["password"])
        self.assertTrue("数字" in password_errors or "numeric" in password_errors.lower())

    def test_register_accepts_password_confirm(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "register_ok",
                "email": "ok@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(User.objects.filter(username="register_ok").exists())

    def test_register_ignores_whitespace_in_credentials(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": " register space ",
                "email": " space @example.com ",
                "password": " Strong Pass 123 ! ",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="registerspace", email="space@example.com").exists())


class LoginApiTests(APITestCase):
    def test_login_ignores_whitespace_in_credentials(self):
        User.objects.create_user(
            username="loginspace",
            email="loginspace@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": " login space ",
                "password": " Strong Pass 123 ! ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])


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
