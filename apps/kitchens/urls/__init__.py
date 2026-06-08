from django.urls import include, path

from .stock import urlpatterns as stock_urls

app_name = "kitchens"

urlpatterns = [
    path("stock/", include(stock_urls)),
]
