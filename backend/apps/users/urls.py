from django.urls import path

from apps.users.views import (
    DynamicProfileView,
    EmailCodeView,
    LoginView,
    PasswordResetView,
    ProfileMetaView,
    ProfilePromptAckView,
    ProfilePromptStatusView,
    ProfileView,
    RefreshView,
    RegisterView,
    StableProfileView,
)

urlpatterns = [
    path("auth/email-code/", EmailCodeView.as_view(), name="email-code"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("me/", ProfileView.as_view(), name="profile"),
    path("profile/meta/", ProfileMetaView.as_view(), name="profile-meta"),
    path("profile/prompts/", ProfilePromptStatusView.as_view(), name="profile-prompts"),
    path("profile/prompts/ack/", ProfilePromptAckView.as_view(), name="profile-prompts-ack"),
    path("profile/stable/", StableProfileView.as_view(), name="profile-stable"),
    path("profile/dynamic/", DynamicProfileView.as_view(), name="profile-dynamic"),
]
