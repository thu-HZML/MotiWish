from rest_framework import serializers

from apps.common.models import LegalDocument


class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = (
            "id",
            "document_type",
            "title",
            "version",
            "summary",
            "content",
            "effective_at",
            "prompt_notes",
            "updated_at",
        )
