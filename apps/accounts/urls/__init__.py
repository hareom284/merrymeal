from django.urls import include, path

from .application import urlpatterns as application_urls
from .auth import urlpatterns as auth_urls
from .password_reset import urlpatterns as password_reset_urls

app_name = "accounts"

urlpatterns = [
    path("accounts/", include(auth_urls + password_reset_urls)),
    path("apply/", include(application_urls)),
]
