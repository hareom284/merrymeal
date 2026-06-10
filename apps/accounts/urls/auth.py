from django.urls import path

from apps.accounts.views.auth import login_view, logout_view
from apps.accounts.views.set_password import set_password_view

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("set-password/", set_password_view, name="set_password"),
]
