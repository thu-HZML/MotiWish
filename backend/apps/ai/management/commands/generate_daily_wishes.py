from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.timezones import business_localdate
from apps.ai.services import generate_daily_wish_refresh


class Command(BaseCommand):
    help = "Generate one pending AI wish candidate for each active user for a given date."

    def add_arguments(self, parser):
        parser.add_argument("--date", dest="date", help="Refresh date in YYYY-MM-DD. Defaults to today.")
        parser.add_argument("--user-id", dest="user_id", type=int, help="Only generate for one user.")
        parser.add_argument("--force", action="store_true", help="Regenerate even if a candidate already exists.")

    def handle(self, *args, **options):
        refresh_date = timezone.datetime.fromisoformat(options["date"]).date() if options.get("date") else business_localdate()
        users = get_user_model().objects.filter(is_active=True)
        if options.get("user_id"):
            users = users.filter(pk=options["user_id"])

        created_count = 0
        reused_count = 0
        for user in users.iterator():
            _, created = generate_daily_wish_refresh(
                user=user,
                refresh_date=refresh_date,
                force=options["force"],
            )
            if created:
                created_count += 1
            else:
                reused_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Daily wish refresh completed for {refresh_date}: created={created_count}, reused={reused_count}."
            )
        )
