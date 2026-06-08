from django.utils import timezone

from apps.common.timezones import business_timezone


class BusinessTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(business_timezone())
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
