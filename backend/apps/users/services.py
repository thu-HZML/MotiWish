import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.users.models import EmailVerificationCode, User


EMAIL_CODE_EXPIRE_MINUTES = 10
EMAIL_CODE_RESEND_INTERVAL_SECONDS = 60
EMAIL_CODE_HOURLY_LIMIT = 5
EMAIL_CODE_MAX_ATTEMPTS = 5


def normalize_email(email):
    return User.objects.normalize_email(email).strip().lower()


def _generate_numeric_code():
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def _email_subject(purpose):
    if purpose == EmailVerificationCode.Purpose.PASSWORD_RESET:
        return "MotiWish password reset code"
    return "MotiWish registration verification code"


def _email_body(code, purpose):
    action = "reset your password" if purpose == EmailVerificationCode.Purpose.PASSWORD_RESET else "complete registration"
    return (
        f"Your MotiWish verification code is: {code}\n\n"
        f"Use this code to {action}. It expires in {EMAIL_CODE_EXPIRE_MINUTES} minutes.\n"
        "If you did not request this code, you can ignore this email."
    )


def _client_ip(request):
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def validate_email_purpose_target(*, email, purpose):
    normalized = normalize_email(email)
    exists = User.objects.filter(email__iexact=normalized).exists()
    if purpose == EmailVerificationCode.Purpose.REGISTER and exists:
        raise ValueError("该邮箱已被注册。")
    if purpose == EmailVerificationCode.Purpose.PASSWORD_RESET and not exists:
        raise ValueError("该邮箱尚未注册。")
    return normalized


@transaction.atomic
def send_email_verification_code(*, email, purpose, request=None):
    normalized = validate_email_purpose_target(email=email, purpose=purpose)
    now = timezone.now()

    recent = EmailVerificationCode.objects.filter(
        email__iexact=normalized,
        purpose=purpose,
        created_at__gte=now - timedelta(seconds=EMAIL_CODE_RESEND_INTERVAL_SECONDS),
    ).first()
    if recent:
        raise ValueError("验证码发送过于频繁，请稍后再试。")

    hourly_count = EmailVerificationCode.objects.filter(
        email__iexact=normalized,
        purpose=purpose,
        created_at__gte=now - timedelta(hours=1),
    ).count()
    if hourly_count >= EMAIL_CODE_HOURLY_LIMIT:
        raise ValueError("验证码发送次数过多，请一小时后再试。")

    code = _generate_numeric_code()
    EmailVerificationCode.objects.create(
        email=normalized,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=EMAIL_CODE_EXPIRE_MINUTES),
        sent_ip=_client_ip(request),
    )
    send_mail(
        subject=_email_subject(purpose),
        message=_email_body(code, purpose),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[normalized],
        fail_silently=False,
    )
    return {
        "email": normalized,
        "purpose": purpose,
        "expires_in_seconds": EMAIL_CODE_EXPIRE_MINUTES * 60,
        "resend_after_seconds": EMAIL_CODE_RESEND_INTERVAL_SECONDS,
    }


@transaction.atomic
def consume_email_verification_code(*, email, purpose, code):
    normalized = normalize_email(email)
    verification = (
        EmailVerificationCode.objects.select_for_update()
        .filter(email__iexact=normalized, purpose=purpose, used_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if verification is None:
        raise ValueError("验证码无效或已过期。")

    if verification.is_expired:
        verification.attempt_count += 1
        verification.save(update_fields=["attempt_count", "updated_at"])
        raise ValueError("验证码无效或已过期。")

    if verification.attempt_count >= EMAIL_CODE_MAX_ATTEMPTS:
        raise ValueError("验证码尝试次数过多，请重新获取。")

    verification.attempt_count += 1
    if not check_password(code, verification.code_hash):
        verification.save(update_fields=["attempt_count", "updated_at"])
        raise ValueError("验证码错误。")

    verification.used_at = timezone.now()
    verification.save(update_fields=["attempt_count", "used_at", "updated_at"])
    return verification


@transaction.atomic
def grant_experience(*, user, amount):
    if amount <= 0:
        raise ValueError("经验值必须为正数")

    user = user.__class__.objects.select_for_update().get(pk=user.pk)
    before = {
        "level": user.level,
        "experience": user.experience,
        "total_experience": user.total_experience,
    }

    user.experience += amount
    user.total_experience += amount
    leveled_up = False

    while user.experience >= user.next_level_experience:
        user.experience -= user.next_level_experience
        user.level += 1
        leveled_up = True

    user.save(update_fields=["level", "experience", "total_experience", "updated_at"])
    return {
        "before": before,
        "after": {
            "level": user.level,
            "experience": user.experience,
            "total_experience": user.total_experience,
            "next_level_experience": user.next_level_experience,
        },
        "gained_experience": amount,
        "leveled_up": leveled_up,
    }
