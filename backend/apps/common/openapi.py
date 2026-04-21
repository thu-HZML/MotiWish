from rest_framework import serializers
from drf_spectacular.utils import inline_serializer


def api_envelope_serializer(name, data_field):
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(),
            "code": serializers.CharField(),
            "message": serializers.CharField(),
            "data": data_field,
        },
    )
