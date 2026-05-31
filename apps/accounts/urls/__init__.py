from .auth import urlpatterns as auth_urls
from .password_reset import urlpatterns as password_reset_urls

app_name = "accounts"

urlpatterns = auth_urls + password_reset_urls
