from django.urls import path

from apps.users.views import LoginView, ProfileView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("me/", ProfileView.as_view(), name="profile"),
]
