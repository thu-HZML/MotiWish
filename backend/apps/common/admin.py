from django.contrib import admin

from apps.common.models import LegalDocument


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "document_type", "title", "version", "effective_at", "is_active")
    list_filter = ("document_type", "is_active")
    search_fields = ("title", "version", "summary")
