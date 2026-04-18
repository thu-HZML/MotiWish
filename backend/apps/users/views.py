from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.users.serializers import AuthTokenSerializer, LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_response(data=AuthTokenSerializer.from_user(user), message="注册成功")


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return api_response(
            data=AuthTokenSerializer.from_user(serializer.validated_data["user"]),
            message="登录成功",
        )


class ProfileView(APIView):
    def get(self, request):
        return api_response(data=UserSerializer(request.user).data, message="获取个人信息成功")
