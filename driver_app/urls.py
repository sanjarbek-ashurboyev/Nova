from django.urls import path

from driver_app.views import (
    AvailableOrdersListView,
    DriverDeliverOrderView,
    DriverOrdersListView,
    DriverTakeOrderView,
)

app_name = 'driver'

urlpatterns = [
    path('orders/', AvailableOrdersListView.as_view(), name='available-orders'),
    path('orders/<int:pk>/take/', DriverTakeOrderView.as_view(), name='take-order'),
    path('my-orders/', DriverOrdersListView.as_view(), name='my-orders'),
    path('my-orders/<int:pk>/deliver/', DriverDeliverOrderView.as_view(), name='deliver-order'),
]
