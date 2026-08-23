from django.urls import path

from accounts.views import (
    CabinetDetailView,
    LoginView,
    LogoutView,
    ReferralListView,
    RegisterView,
    SettingsPasswordUpdateView,
    SettingsUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('my-cabinet/', CabinetDetailView.as_view(), name='cabinet'),
    path('my-cabinet/settings/', SettingsUpdateView.as_view(), name='cabinet-settings'),
    path('my-cabinet/settings/password/', SettingsPasswordUpdateView.as_view(), name='cabinet-password'),
    path('my-cabinet/referrals/', ReferralListView.as_view(), name='cabinet-referrals'),
]