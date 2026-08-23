from django.urls import path

from orders.views import (
    OrderSurveyListView,
    PaymentReceiptDownloadView,
    PaymentRequestView,
    SellerContestListView,
    ThreadStatsListView,
)

app_name = 'orders'

urlpatterns = [
    path('my-cabinet/payments/', PaymentRequestView.as_view(), name='cabinet-payments'),
    path('my-cabinet/payments/<int:pk>/receipt/', PaymentReceiptDownloadView.as_view(), name='payment-receipt'),
    path('my-cabinet/stats/', ThreadStatsListView.as_view(), name='cabinet-stats'),
    path('my-cabinet/contest/', SellerContestListView.as_view(), name='cabinet-contest'),
    path('my-cabinet/surveys/', OrderSurveyListView.as_view(), name='cabinet-surveys'),
]