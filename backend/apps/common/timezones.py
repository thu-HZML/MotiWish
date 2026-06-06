from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def business_timezone():
    return ZoneInfo(getattr(settings, "BUSINESS_TIME_ZONE", settings.TIME_ZONE))


def business_now():
    return timezone.localtime(timezone.now(), business_timezone())


def business_localdate(value=None):
    if value is None:
        return business_now().date()
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, business_timezone())
        return timezone.localtime(value, business_timezone()).date()
    if isinstance(value, date):
        return value
    return None


def parse_user_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, business_timezone())
    return parsed


def format_business_datetime(value):
    parsed = parse_user_datetime(value)
    if parsed is None:
        return None
    return timezone.localtime(parsed, business_timezone()).isoformat()
