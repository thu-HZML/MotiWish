from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.tasks.services import sync_overdue_one_time_tasks


class Command(BaseCommand):
    help = "Sync overdue one-time tasks and mark pending occurrences as missed."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, default=None, help="Only sync tasks for this user id.")

    def handle(self, *args, **options):
        user = None
        user_id = options.get("user_id")
        if user_id:
            User = get_user_model()
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist as exc:
                raise CommandError(f"User {user_id} does not exist.") from exc

        result = sync_overdue_one_time_tasks(user=user)
        self.stdout.write(
            self.style.SUCCESS(
                "Synced overdue tasks: "
                f"checked={result['checked_count']}, missed={result['missed_count']}, "
                f"synced_at={result['synced_at']}"
            )
        )
