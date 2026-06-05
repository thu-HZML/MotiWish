from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import DynamicProfile, StableProfile, User


def _remove_whitespace_chars(value):
    if isinstance(value, str):
        return "".join(value.split())
    return value


class AuthWhitespaceNormalizerMixin:
    whitespace_normalized_fields = ()

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            for field in self.whitespace_normalized_fields:
                if field in data:
                    data[field] = _remove_whitespace_chars(data[field])
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    display_nickname = serializers.CharField(read_only=True)
    default_avatar_group = serializers.CharField(read_only=True)
    next_level_experience = serializers.IntegerField(read_only=True)
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
            "education_stage",
            "language_preference",
            "region",
            "bio",
            "timezone",
            "long_term_goals",
            "focus_areas",
            "onboarding_completed",
            "basic_profile_completed",
            "basic_profile_completion_score",
            "basic_profile_missing_fields",
            "basic_profile_last_prompted_at",
            "level",
            "experience",
            "total_experience",
            "next_level_experience",
            "prompt_profile",
        )
        read_only_fields = (
            "id",
            "display_nickname",
            "avatar_url",
            "default_avatar_group",
            "onboarding_completed",
            "basic_profile_completed",
            "basic_profile_completion_score",
            "basic_profile_missing_fields",
            "basic_profile_last_prompted_at",
            "level",
            "experience",
            "total_experience",
            "next_level_experience",
            "prompt_profile",
        )

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


class RegisterSerializer(AuthWhitespaceNormalizerMixin, serializers.ModelSerializer):
    whitespace_normalized_fields = ("username", "email", "password", "password_confirm")

    password = serializers.CharField(
        write_only=True,
        help_text="登录密码。当前规则：至少 8 位，不能与用户信息过于相似，不能是常见弱密码，不能全为数字；空白字符会被服务端忽略，不作为有效密码字符。",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="确认密码，必须与 password 完全一致；空白字符会被服务端忽略。",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "nickname",
            "gender",
            "occupation",
            "education_stage",
            "language_preference",
            "bio",
            "timezone",
            "long_term_goals",
            "focus_areas",
        )

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")
        errors = {}

        if password and password_confirm and password != password_confirm:
            errors["password_confirm"] = ["两次输入的密码不一致。"]

        if password:
            user_attrs = {
                key: value
                for key, value in attrs.items()
                if key not in {"password", "password_confirm"}
            }
            try:
                validate_password(password, user=User(**user_attrs))
            except DjangoValidationError as exc:
                errors["password"] = list(exc.messages)

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_confirm", None)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(AuthWhitespaceNormalizerMixin, serializers.Serializer):
    whitespace_normalized_fields = ("username", "password")

    username = serializers.CharField(help_text="用户名。空白字符会被服务端忽略。")
    password = serializers.CharField(write_only=True, help_text="登录密码。空白字符会被服务端忽略。")

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("用户名或密码错误。")
        attrs["user"] = user
        return attrs


class BaseProfileUpdateSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(required=False, allow_blank=True, help_text="昵称。为空时展示默认昵称。")
    avatar = serializers.ImageField(required=False, allow_null=True, help_text="头像图片文件，可为空。")
    birth_date = serializers.DateField(required=False, allow_null=True, help_text="生日，可为空。")
    region = serializers.CharField(required=False, allow_blank=True, help_text="所在地区，可为空。")
    bio = serializers.CharField(required=False, allow_blank=True, help_text="个人签名，最长 100 字符。")
    timezone = serializers.CharField(required=False, help_text="时区，例如 Asia/Shanghai。")
    long_term_goals = serializers.ListField(
        child=serializers.ChoiceField(choices=User.GoalCategory.choices),
        required=False,
        help_text='长期目标类型，多选；如果跳过，请传 ["unspecified"]。',
    )
    focus_areas = serializers.ListField(
        child=serializers.ChoiceField(choices=User.FocusArea.choices),
        required=False,
        help_text='当前主要关注领域，多选；如果跳过，请传 ["unspecified"]。',
    )

    class Meta:
        model = User
        fields = (
            "nickname",
            "avatar",
            "gender",
            "birth_date",
            "occupation",
            "education_stage",
            "language_preference",
            "region",
            "bio",
            "timezone",
            "long_term_goals",
            "focus_areas",
        )


class StableProfileSerializer(serializers.ModelSerializer):
    should_prompt = serializers.BooleanField(read_only=True)
    next_prompt_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = StableProfile
        fields = (
            "self_management_challenges",
            "motivation_preferences",
            "reward_preference",
            "penalty_tolerance",
            "stress_sensitivity",
            "self_discipline_score",
            "chronotype",
            "energy_peak_periods",
            "task_granularity_preference",
            "planning_style_preference",
            "is_completed",
            "completion_score",
            "missing_fields",
            "last_prompted_at",
            "next_prompt_at",
            "questionnaire_completed_at",
            "should_prompt",
        )
        read_only_fields = (
            "is_completed",
            "completion_score",
            "missing_fields",
            "last_prompted_at",
            "next_prompt_at",
            "questionnaire_completed_at",
            "should_prompt",
        )

    def validate_self_discipline_score(self, value):
        if value is not None and not 1 <= value <= 10:
            raise serializers.ValidationError("self_discipline_score 必须在 1 到 10 之间。")
        return value


class DynamicProfileSerializer(serializers.ModelSerializer):
    should_prompt = serializers.BooleanField(read_only=True)
    next_prompt_at = serializers.DateTimeField(read_only=True)
    has_meaningful_data = serializers.BooleanField(read_only=True)

    class Meta:
        model = DynamicProfile
        fields = (
            "current_stage_tags",
            "stress_level",
            "sleep_quality",
            "mood_state",
            "available_time_level",
            "current_top_goal",
            "current_main_blocker",
            "weekly_time_budget_hours",
            "last_prompted_at",
            "next_prompt_at",
            "should_prompt",
            "has_meaningful_data",
        )
        read_only_fields = (
            "last_prompted_at",
            "next_prompt_at",
            "should_prompt",
            "has_meaningful_data",
        )

    def validate_stress_level(self, value):
        if value is not None and not 1 <= value <= 5:
            raise serializers.ValidationError("stress_level 必须在 1 到 5 之间。")
        return value


class ProfileMetaSerializer(serializers.Serializer):
    basic = serializers.JSONField(help_text="基础信息层元数据，前端可据此渲染注册后补全表单。")
    stable = serializers.JSONField(help_text="稳定画像问卷元数据，前端可据此渲染问卷页面。")
    dynamic = serializers.JSONField(help_text="动态状态元数据，前端可据此渲染轻提示表单。")
    reminder_policy = serializers.JSONField(help_text="三层画像的提醒策略说明。")


class ProfilePromptStatusSerializer(serializers.Serializer):
    basic = serializers.JSONField(help_text="基础信息层当前的完善度和提醒状态。")
    stable = serializers.JSONField(help_text="稳定画像层当前的问卷完成度和提醒状态。")
    dynamic = serializers.JSONField(help_text="动态状态层当前的提示状态。")


class ReminderAckSerializer(serializers.Serializer):
    layer = serializers.ChoiceField(
        choices=("basic", "stable", "dynamic"),
        help_text="本次确认已展示的提醒层级：basic、stable 或 dynamic。",
    )


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
