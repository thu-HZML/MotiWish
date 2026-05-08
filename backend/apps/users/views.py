from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.common.api import api_response
from apps.common.openapi import api_envelope_serializer
from apps.users.models import DynamicProfile, StableProfile, User
from apps.users.serializers import (
    BaseProfileUpdateSerializer,
    DynamicProfileSerializer,
    JWTTokenSerializer,
    LoginSerializer,
    ProfileMetaSerializer,
    ProfilePromptStatusSerializer,
    RegisterSerializer,
    ReminderAckSerializer,
    StableProfileSerializer,
    UserSerializer,
)


def _get_profile_meta():
    return {
        "basic": {
            "title": "基础信息层",
            "required_after_register": True,
            "allow_skip_with_sentinel": True,
            "fields": [
                {"key": "nickname", "label": "昵称", "required": True, "type": "string"},
                {"key": "avatar", "label": "头像", "required": False, "type": "image"},
                {
                    "key": "gender",
                    "label": "性别",
                    "required": True,
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in User.Gender.choices],
                },
                {"key": "birth_date", "label": "生日", "required": False, "type": "date"},
                {
                    "key": "occupation",
                    "label": "职业",
                    "required": True,
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in User.Occupation.choices],
                },
                {
                    "key": "education_stage",
                    "label": "教育阶段",
                    "required": True,
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in User.EducationStage.choices],
                },
                {
                    "key": "language_preference",
                    "label": "语言偏好",
                    "required": True,
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in User.LanguagePreference.choices],
                },
                {"key": "region", "label": "所在地区", "required": False, "type": "string"},
                {"key": "bio", "label": "个人签名", "required": False, "type": "string"},
                {"key": "timezone", "label": "时区", "required": True, "type": "string"},
                {
                    "key": "long_term_goals",
                    "label": "长期目标类型",
                    "required": True,
                    "type": "multi_choice",
                    "options": [{"value": key, "label": label} for key, label in User.GoalCategory.choices],
                },
                {
                    "key": "focus_areas",
                    "label": "当前主要关注领域",
                    "required": True,
                    "type": "multi_choice",
                    "options": [{"value": key, "label": label} for key, label in User.FocusArea.choices],
                },
            ],
        },
        "stable": {
            "title": "稳定画像问卷",
            "interaction": "questionnaire",
            "questions": [
                {
                    "key": "self_management_challenges",
                    "title": "你在自我管理中最常遇到哪些困难？",
                    "type": "multi_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.SelfManagementChallenge.choices],
                },
                {
                    "key": "motivation_preferences",
                    "title": "什么最能驱动你持续完成任务？",
                    "type": "multi_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.MotivationPreference.choices],
                },
                {
                    "key": "reward_preference",
                    "title": "你更喜欢哪种奖励方式？",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.RewardPreference.choices],
                },
                {
                    "key": "penalty_tolerance",
                    "title": "你对惩罚机制的接受度如何？",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.ToleranceLevel.choices],
                },
                {
                    "key": "stress_sensitivity",
                    "title": "当压力增加时，你会受到多大影响？",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.ToleranceLevel.choices],
                },
                {"key": "self_discipline_score", "title": "如果满分 10 分，你会给自己的自律程度打几分？", "type": "scale", "min": 1, "max": 10},
                {
                    "key": "chronotype",
                    "title": "你更接近哪种作息类型？",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.Chronotype.choices],
                },
                {
                    "key": "energy_peak_periods",
                    "title": "你通常在哪些时段精力更好？",
                    "type": "multi_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.EnergyPeakPeriod.choices],
                },
                {
                    "key": "task_granularity_preference",
                    "title": "你更喜欢怎样的任务粒度？",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.TaskGranularityPreference.choices],
                },
                {
                    "key": "planning_style_preference",
                    "title": "你更偏好怎样的计划方式？",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in StableProfile.PlanningStylePreference.choices],
                },
            ],
        },
        "dynamic": {
            "title": "动态状态层",
            "interaction": "light_prompt",
            "fields": [
                {
                    "key": "current_stage_tags",
                    "label": "当前阶段标签",
                    "type": "multi_choice",
                    "options": [{"value": key, "label": label} for key, label in DynamicProfile.StageTag.choices],
                },
                {"key": "stress_level", "label": "最近压力水平", "type": "scale", "min": 1, "max": 5},
                {
                    "key": "sleep_quality",
                    "label": "最近睡眠情况",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in DynamicProfile.ThreeLevelState.choices],
                },
                {
                    "key": "mood_state",
                    "label": "最近情绪状态",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in DynamicProfile.ThreeLevelState.choices],
                },
                {
                    "key": "available_time_level",
                    "label": "最近可支配时间",
                    "type": "single_choice",
                    "options": [{"value": key, "label": label} for key, label in DynamicProfile.AvailableTimeLevel.choices],
                },
                {"key": "current_top_goal", "label": "当前最重要目标", "type": "string"},
                {"key": "current_main_blocker", "label": "当前最大阻碍", "type": "string"},
                {"key": "weekly_time_budget_hours", "label": "本周可投入时长（小时）", "type": "integer"},
            ],
        },
        "reminder_policy": {
            "basic": "基础信息未完善时可持续提醒；前端可根据 basic_profile_completed 与 basic_profile_missing_fields 展示提醒。",
            "stable": f"稳定画像未完成时建议每 {StableProfile.PROMPT_INTERVAL_DAYS} 天提醒一次，适合 AI 悬浮球问卷入口。",
            "dynamic": f"动态状态默认每 {DynamicProfile.PROMPT_INTERVAL_DAYS} 天轻提示一次，可直接跳过。",
        },
    }


def _build_prompt_status(user):
    stable_profile, _ = StableProfile.objects.get_or_create(user=user)
    dynamic_profile, _ = DynamicProfile.objects.get_or_create(user=user)
    return {
        "basic": {
            "completed": user.basic_profile_completed,
            "completion_score": user.basic_profile_completion_score,
            "missing_fields": user.basic_profile_missing_fields,
            "last_prompted_at": user.basic_profile_last_prompted_at,
            "should_prompt": not user.basic_profile_completed,
        },
        "stable": {
            "completed": stable_profile.is_completed,
            "completion_score": stable_profile.completion_score,
            "missing_fields": stable_profile.missing_fields,
            "last_prompted_at": stable_profile.last_prompted_at,
            "next_prompt_at": stable_profile.next_prompt_at,
            "should_prompt": stable_profile.should_prompt,
        },
        "dynamic": {
            "has_meaningful_data": dynamic_profile.has_meaningful_data,
            "last_prompted_at": dynamic_profile.last_prompted_at,
            "next_prompt_at": dynamic_profile.next_prompt_at,
            "should_prompt": dynamic_profile.should_prompt,
        },
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="用户注册",
        description="注册完成后会直接返回 JWT 令牌和用户基础资料。前端通常应在注册成功后立即进入基础资料完善流程。",
        request=RegisterSerializer,
        responses=api_envelope_serializer("RegisterResponse", JWTTokenSerializer()),
        examples=[
            OpenApiExample(
                "最小注册请求",
                value={
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": "Password123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "带基础画像的注册请求",
                value={
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": "Password123",
                    "nickname": "爱丽丝",
                    "gender": "female",
                    "occupation": "student",
                    "education_stage": "college",
                    "language_preference": "zh-hans",
                    "bio": "把每天过成自己想要的样子",
                    "timezone": "Asia/Shanghai",
                    "long_term_goals": ["learning", "habit"],
                    "focus_areas": ["exam", "sleep"],
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        StableProfile.objects.get_or_create(user=user)
        DynamicProfile.objects.get_or_create(user=user)
        return api_response(data=JWTTokenSerializer.from_user(user, request), message="注册成功")


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="用户登录",
        description="返回 access token、refresh token 和当前用户资料。后续受保护接口都需要在 Authorization 头中带 Bearer access_token。",
        request=LoginSerializer,
        responses=api_envelope_serializer("LoginResponse", JWTTokenSerializer()),
        examples=[
            OpenApiExample("登录请求", value={"username": "alice", "password": "Password123"}, request_only=True),
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return api_response(
            data=JWTTokenSerializer.from_user(serializer.validated_data["user"], request),
            message="登录成功",
        )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="刷新 JWT",
        description="使用 refresh token 获取新的 access token。适合前端在 access token 过期后静默续期。",
        examples=[
            OpenApiExample("刷新令牌请求", value={"refresh": "eyJhbGciOiJIUzI1NiIs..."}, request_only=True),
        ],
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.data = {"success": True, "code": "OK", "message": "刷新令牌成功", "data": response.data}
        return response


class ProfileView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="获取当前用户基础资料",
        description=(
            "返回当前用户的基础信息层数据，以及基础资料完善状态。"
            "前端可根据 basic_profile_completed、basic_profile_completion_score、"
            "basic_profile_missing_fields 决定是否展示完善提醒。"
        ),
        responses=api_envelope_serializer("ProfileResponse", UserSerializer()),
    )
    def get(self, request):
        return api_response(
            data=UserSerializer(request.user, context={"request": request}).data,
            message="获取个人信息成功",
        )

    @extend_schema(
        tags=["Users"],
        summary="更新当前用户基础资料",
        description=(
            "用于注册后基础资料完善页面。"
            "基础层可允许跳过：若用户不想填写某个多选项，请传 ['unspecified'] 作为哑元值。"
        ),
        request=BaseProfileUpdateSerializer,
        responses=api_envelope_serializer("ProfileUpdateResponse", UserSerializer()),
        examples=[
            OpenApiExample(
                "完整填写基础资料",
                value={
                    "nickname": "时间炼金师",
                    "gender": "male",
                    "birth_date": "2003-09-10",
                    "occupation": "student",
                    "education_stage": "college",
                    "language_preference": "zh-hans",
                    "region": "北京",
                    "bio": "把每一天炼成愿望的燃料",
                    "timezone": "Asia/Shanghai",
                    "long_term_goals": ["learning", "habit"],
                    "focus_areas": ["exam", "sleep"],
                },
                request_only=True,
            ),
            OpenApiExample(
                "跳过部分多选项",
                value={
                    "nickname": "时间炼金师",
                    "gender": "unknown",
                    "occupation": "undisclosed",
                    "education_stage": "undisclosed",
                    "language_preference": "zh-hans",
                    "timezone": "Asia/Shanghai",
                    "long_term_goals": ["unspecified"],
                    "focus_areas": ["unspecified"],
                },
                request_only=True,
            ),
        ],
    )
    def patch(self, request):
        serializer = BaseProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_response(
            data=UserSerializer(user, context={"request": request}).data,
            message="更新个人信息成功",
        )


class StableProfileView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="获取稳定画像问卷结果",
        description="返回稳定画像问卷当前填写结果，以及完成度、缺失字段和下一次建议提醒时间。",
        responses=api_envelope_serializer("StableProfileResponse", StableProfileSerializer()),
    )
    def get(self, request):
        profile, _ = StableProfile.objects.get_or_create(user=request.user)
        return api_response(data=StableProfileSerializer(profile).data, message="获取稳定画像成功")

    @extend_schema(
        tags=["Users"],
        summary="提交或更新稳定画像问卷",
        description="AI 悬浮球或问卷页提交稳定画像时调用。前端可分步保存，也可一次性提交全部答案。",
        request=StableProfileSerializer,
        responses=api_envelope_serializer("StableProfileUpdateResponse", StableProfileSerializer()),
        examples=[
            OpenApiExample(
                "提交稳定画像问卷",
                value={
                    "self_management_challenges": ["procrastination", "distraction"],
                    "motivation_preferences": ["achievement", "narrative"],
                    "reward_preference": "instant",
                    "penalty_tolerance": "medium",
                    "stress_sensitivity": "high",
                    "self_discipline_score": 6,
                    "chronotype": "night",
                    "energy_peak_periods": ["evening", "late_night"],
                    "task_granularity_preference": "small",
                    "planning_style_preference": "mixed",
                },
                request_only=True,
            )
        ],
    )
    def patch(self, request):
        profile, _ = StableProfile.objects.get_or_create(user=request.user)
        serializer = StableProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return api_response(data=StableProfileSerializer(profile).data, message="更新稳定画像成功")


class DynamicProfileView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="获取动态状态画像",
        description="返回动态状态层数据。该层允许长期为空，主要用于 AI 结合最近状态做轻量调节。",
        responses=api_envelope_serializer("DynamicProfileResponse", DynamicProfileSerializer()),
    )
    def get(self, request):
        profile, _ = DynamicProfile.objects.get_or_create(user=request.user)
        return api_response(data=DynamicProfileSerializer(profile).data, message="获取动态状态成功")

    @extend_schema(
        tags=["Users"],
        summary="提交或更新动态状态画像",
        description="用于每周轻提示或用户主动更新最近状态。字段均可部分提交。",
        request=DynamicProfileSerializer,
        responses=api_envelope_serializer("DynamicProfileUpdateResponse", DynamicProfileSerializer()),
        examples=[
            OpenApiExample(
                "更新动态状态",
                value={
                    "current_stage_tags": ["exam", "crunch"],
                    "stress_level": 4,
                    "sleep_quality": "medium",
                    "mood_state": "medium",
                    "available_time_level": "limited",
                    "current_top_goal": "完成本周数据库课程项目",
                    "current_main_blocker": "白天课程多，晚上容易分心",
                    "weekly_time_budget_hours": 8,
                },
                request_only=True,
            )
        ],
    )
    def patch(self, request):
        profile, _ = DynamicProfile.objects.get_or_create(user=request.user)
        serializer = DynamicProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return api_response(data=DynamicProfileSerializer(profile).data, message="更新动态状态成功")


class ProfileMetaView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="获取画像元信息",
        description=(
            "返回前端构建基础资料表单、稳定画像问卷、动态状态轻提示所需的全部元数据。"
            "推荐在应用启动或进入个人中心时拉取一次并缓存。"
        ),
        responses=api_envelope_serializer("ProfileMetaResponse", ProfileMetaSerializer()),
        examples=[
            OpenApiExample(
                "画像元信息响应片段",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "获取画像元信息成功",
                    "data": {
                        "basic": {
                            "title": "基础信息层",
                            "required_after_register": True,
                            "allow_skip_with_sentinel": True,
                        },
                        "stable": {"title": "稳定画像问卷", "interaction": "questionnaire"},
                        "dynamic": {"title": "动态状态层", "interaction": "light_prompt"},
                        "reminder_policy": {
                            "basic": "基础信息未完善时可持续提醒。",
                            "stable": "稳定画像未完成时建议低频提醒。",
                            "dynamic": "动态状态默认每周轻提示一次。",
                        },
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        return api_response(data=_get_profile_meta(), message="获取画像元信息成功")


class ProfilePromptStatusView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="获取画像提醒状态",
        description=(
            "用于前端决定是否展示基础资料提醒、稳定画像问卷入口或动态状态轻提示。"
            "推荐在用户登录后和首页进入时调用。"
        ),
        responses=api_envelope_serializer("ProfilePromptStatusResponse", ProfilePromptStatusSerializer()),
        examples=[
            OpenApiExample(
                "提醒状态响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "获取提醒状态成功",
                    "data": {
                        "basic": {
                            "completed": False,
                            "completion_score": 62,
                            "missing_fields": ["occupation", "long_term_goals", "focus_areas"],
                            "last_prompted_at": None,
                            "should_prompt": True,
                        },
                        "stable": {
                            "completed": False,
                            "completion_score": 30,
                            "missing_fields": ["motivation_preferences", "chronotype"],
                            "last_prompted_at": "2026-04-27T20:00:00+08:00",
                            "next_prompt_at": "2026-04-30T20:00:00+08:00",
                            "should_prompt": False,
                        },
                        "dynamic": {
                            "has_meaningful_data": True,
                            "last_prompted_at": "2026-04-22T10:00:00+08:00",
                            "next_prompt_at": "2026-04-29T10:00:00+08:00",
                            "should_prompt": True,
                        },
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        return api_response(data=_build_prompt_status(request.user), message="获取提醒状态成功")


class ProfilePromptAckView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="记录画像提醒已展示",
        description=(
            "当前端实际展示了某一层的提醒后调用，用于更新后端的提醒节流时间。"
            "这个接口不会修改画像内容，只记录“提醒已经给用户看过”。"
        ),
        request=ReminderAckSerializer,
        responses=api_envelope_serializer("ProfilePromptAckResponse", ProfilePromptStatusSerializer()),
        examples=[
            OpenApiExample("记录稳定画像提醒已展示", value={"layer": "stable"}, request_only=True),
            OpenApiExample("记录动态状态提醒已展示", value={"layer": "dynamic"}, request_only=True),
        ],
    )
    def post(self, request):
        serializer = ReminderAckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        layer = serializer.validated_data["layer"]
        if layer == "basic":
            request.user.mark_basic_profile_prompted()
        elif layer == "stable":
            profile, _ = StableProfile.objects.get_or_create(user=request.user)
            profile.mark_prompted()
        else:
            profile, _ = DynamicProfile.objects.get_or_create(user=request.user)
            profile.mark_prompted()
        return api_response(data=_build_prompt_status(request.user), message="记录提醒状态成功")
