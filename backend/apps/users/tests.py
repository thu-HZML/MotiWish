from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.users.models import DynamicProfile, EmailVerificationCode, StableProfile, User


def create_email_code(*, email, purpose, code="123456", expires_at=None, created_at=None):
    verification = EmailVerificationCode.objects.create(
        email=email,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=expires_at or timezone.now() + timedelta(minutes=10),
    )
    if created_at is not None:
        EmailVerificationCode.objects.filter(pk=verification.pk).update(created_at=created_at)
        verification.refresh_from_db()
    return verification


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
        create_email_code(
            email="ok@example.com",
            purpose=EmailVerificationCode.Purpose.REGISTER,
        )
        response = self.client.post(
            reverse("register"),
            {
                "username": "register_ok",
                "email": "ok@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "email_code": "123456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(User.objects.filter(username="register_ok").exists())

    def test_register_ignores_whitespace_in_credentials(self):
        create_email_code(
            email="space@example.com",
            purpose=EmailVerificationCode.Purpose.REGISTER,
        )
        response = self.client.post(
            reverse("register"),
            {
                "username": " register space ",
                "email": " space @example.com ",
                "password": " Strong Pass 123 ! ",
                "password_confirm": "StrongPass123!",
                "email_code": " 123 456 ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="registerspace", email="space@example.com").exists())

    def test_register_requires_valid_email_code(self):
        create_email_code(
            email="codefail@example.com",
            purpose=EmailVerificationCode.Purpose.REGISTER,
            code="654321",
        )
        response = self.client.post(
            reverse("register"),
            {
                "username": "register_code_fail",
                "email": "codefail@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "email_code": "123456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("email_code", response.data["data"])

    def test_register_rejects_used_email_code(self):
        verification = create_email_code(
            email="used@example.com",
            purpose=EmailVerificationCode.Purpose.REGISTER,
        )
        verification.used_at = timezone.now()
        verification.save(update_fields=["used_at", "updated_at"])

        response = self.client.post(
            reverse("register"),
            {
                "username": "register_used_code",
                "email": "used@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "email_code": "123456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email_code", response.data["data"])


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

    def test_login_accepts_email_case_insensitively(self):
        User.objects.create_user(
            username="email_login",
            email="EmailLogin@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "emaillogin@EXAMPLE.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailCodeApiTests(APITestCase):
    def test_send_register_code_sends_email(self):
        response = self.client.post(
            reverse("email-code"),
            {"email": "new@example.com", "purpose": "register"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(EmailVerificationCode.objects.filter(email="new@example.com").exists())

    def test_send_code_rejects_fast_resend(self):
        self.client.post(
            reverse("email-code"),
            {"email": "resend@example.com", "purpose": "register"},
            format="json",
        )

        response = self.client.post(
            reverse("email-code"),
            {"email": "resend@example.com", "purpose": "register"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_send_password_reset_code_requires_existing_user(self):
        response = self.client.post(
            reverse("email-code"),
            {"email": "missing@example.com", "purpose": "password_reset"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["data"])


class PasswordResetApiTests(APITestCase):
    def test_password_reset_changes_password_and_consumes_code(self):
        user = User.objects.create_user(
            username="reset_user",
            email="reset@example.com",
            password="OldStrongPass123!",
        )
        verification = create_email_code(
            email="reset@example.com",
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
        )

        response = self.client.post(
            reverse("password-reset"),
            {
                "email": "RESET@example.com",
                "code": "123456",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        user.refresh_from_db()
        self.assertFalse(user.check_password("OldStrongPass123!"))
        self.assertTrue(user.check_password("NewStrongPass123!"))
        verification.refresh_from_db()
        self.assertIsNotNone(verification.used_at)

    def test_password_reset_rejects_expired_code(self):
        User.objects.create_user(
            username="expired_reset",
            email="expired@example.com",
            password="OldStrongPass123!",
        )
        create_email_code(
            email="expired@example.com",
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            reverse("password-reset"),
            {
                "email": "expired@example.com",
                "code": "123456",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.data["data"])


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
