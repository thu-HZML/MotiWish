from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    display_nickname = serializers.CharField(read_only=True)
    default_avatar_group = serializers.CharField(read_only=True)
    prompt_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "nickname",
            "display_nickname",
            "avatar",
            "avatar_url",
            "default_avatar_group",
            "gender",
            "birth_date",
            "occupation",
            "bio",
            "timezone",
            "onboarding_completed",
            "prompt_profile",
        )
        read_only_fields = ("id", "display_nickname", "avatar_url", "default_avatar_group", "prompt_profile")

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar_url(self, obj) -> str | None:
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    @extend_schema_field(serializers.JSONField())
    def get_prompt_profile(self, obj) -> dict:
        return obj.build_prompt_profile()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "nickname",
            "gender",
            "birth_date",
            "occupation",
            "bio",
            "timezone",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("用户名或密码错误。")
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("nickname", "avatar", "gender", "birth_date", "occupation", "bio", "timezone")


class JWTTokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @classmethod
    def from_user(cls, user, request=None):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user, context={"request": request}).data,
        }
