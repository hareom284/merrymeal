from django.urls import path

from apps.kitchens.views.stock import stock_receive_view

urlpatterns = [
    path("receive/", stock_receive_view, name="stock_receive"),
]
