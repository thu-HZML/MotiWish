from django.contrib import admin

from apps.tasks.models import Task, TaskOccurrence


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "task_type", "recurrence", "reward_primary", "status", "created_at")
    list_filter = ("task_type", "recurrence", "status")
    search_fields = ("title", "owner__username", "metric_key")


@admin.register(TaskOccurrence)
class TaskOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "owner", "occurrence_date", "status", "progress", "settled_at")
    list_filter = ("status", "occurrence_date")
