from django.urls import path

from apps.users.views import LoginView, ProfileView, RefreshView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("me/", ProfileView.as_view(), name="profile"),
]
