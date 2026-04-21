from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.common.api import api_response
from apps.common.openapi import api_envelope_serializer
from apps.users.serializers import (
    JWTTokenSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="用户注册",
        request=RegisterSerializer,
        responses=api_envelope_serializer("RegisterResponse", JWTTokenSerializer()),
        examples=[
            OpenApiExample(
                "注册请求",
                value={
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": "Password123",
                    "nickname": "爱丽丝",
                    "gender": "female",
                    "occupation": "student",
                    "bio": "今天也要认真完成任务",
                    "timezone": "Asia/Shanghai",
                },
                request_only=True,
            ),
            OpenApiExample(
                "注册成功响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "注册成功",
                    "data": {
                        "access": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh": "eyJhbGciOiJIUzI1NiIs...",
                        "user": {
                            "id": 1,
                            "username": "alice",
                            "email": "alice@example.com",
                            "nickname": "爱丽丝",
                            "display_nickname": "爱丽丝",
                            "avatar": None,
                            "avatar_url": None,
                            "default_avatar_group": "female-default-1",
                            "gender": "female",
                            "birth_date": None,
                            "occupation": "student",
                            "bio": "今天也要认真完成任务",
                            "timezone": "Asia/Shanghai",
                            "onboarding_completed": False,
                            "prompt_profile": {
                                "nickname": "爱丽丝",
                                "gender": "female",
                                "birth_date": None,
                                "occupation": "student",
                                "bio": "今天也要认真完成任务",
                                "timezone": "Asia/Shanghai",
                                "avatar_present": False,
                                "default_avatar_group": "female-default-1",
                            },
                        },
                    },
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_response(
            data=JWTTokenSerializer.from_user(user, request),
            message="注册成功",
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="用户登录",
        request=LoginSerializer,
        responses=api_envelope_serializer("LoginResponse", JWTTokenSerializer()),
        examples=[
            OpenApiExample(
                "登录请求",
                value={"username": "alice", "password": "Password123"},
                request_only=True,
            ),
            OpenApiExample(
                "登录成功响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "登录成功",
                    "data": {
                        "access": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh": "eyJhbGciOiJIUzI1NiIs...",
                        "user": {"id": 1, "username": "alice", "display_nickname": "爱丽丝"},
                    },
                },
                response_only=True,
            ),
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
        examples=[
            OpenApiExample(
                "刷新令牌请求",
                value={"refresh": "eyJhbGciOiJIUzI1NiIs..."},
                request_only=True,
            ),
            OpenApiExample(
                "刷新令牌响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "刷新令牌成功",
                    "data": {"access": "eyJhbGciOiJIUzI1NiIs..."},
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.data = {
            "success": True,
            "code": "OK",
            "message": "刷新令牌成功",
            "data": response.data,
        }
        return response


class ProfileView(APIView):
    @extend_schema(
        tags=["Users"],
        summary="获取当前用户资料",
        responses=api_envelope_serializer("ProfileResponse", UserSerializer()),
    )
    def get(self, request):
        return api_response(
            data=UserSerializer(request.user, context={"request": request}).data,
            message="获取个人信息成功",
        )

    @extend_schema(
        tags=["Users"],
        summary="更新当前用户资料",
        request=ProfileUpdateSerializer,
        responses=api_envelope_serializer("ProfileUpdateResponse", UserSerializer()),
        examples=[
            OpenApiExample(
                "更新资料请求",
                value={
                    "nickname": "时间炼金师",
                    "gender": "male",
                    "birth_date": "2003-09-10",
                    "occupation": "student",
                    "bio": "把每一天炼成愿望的燃料",
                    "timezone": "Asia/Shanghai",
                },
                request_only=True,
            )
        ],
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_response(
            data=UserSerializer(user, context={"request": request}).data,
            message="更新个人信息成功",
        )
