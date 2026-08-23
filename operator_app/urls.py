from django.urls import path

from operator_app.views import (
    NewOrdersListView,
    OperatorOrderDetailView,
    OperatorOrdersListView,
    OperatorOrderUpdateView,
    OperatorTakeNextOrderView,
    OperatorTakeOrderView,
)

app_name = 'operator'

urlpatterns = [
    path('new-orders/', NewOrdersListView.as_view(), name='new-orders'),
    path('new-orders/take/', OperatorTakeOrderView.as_view(), name='take-order'),
    path('new-orders/take-next/', OperatorTakeNextOrderView.as_view(), name='take-next-order'),
    path('my-orders/', OperatorOrdersListView.as_view(), name='my-orders'),
    path('orders/<int:pk>/', OperatorOrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/status/', OperatorOrderUpdateView.as_view(), name='change-status'),
]