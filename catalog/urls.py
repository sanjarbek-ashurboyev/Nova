from django.urls import path

from catalog.views import (
    CategoryDetailView,
    HomeView,
    ProductDetailView,
    ProductListView,
    ProductSearchListView,
    ThreadCreateView,
    ThreadDeleteView,
    ThreadDetailView,
    ThreadListView,
    ThreadMarketListView,
)

app_name = 'catalog'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),

    # Storefront
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/search/', ProductSearchListView.as_view(), name='product-search'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('threads/<int:pk>/', ThreadDetailView.as_view(), name='thread-detail'),

    # Cabinet
    path('my-cabinet/market/', ThreadMarketListView.as_view(), name='cabinet-market'),
    path('my-cabinet/market/<slug:slug>/', ThreadMarketListView.as_view(), name='cabinet-market-category'),
    path('my-cabinet/threads/', ThreadListView.as_view(), name='cabinet-threads'),
    path('my-cabinet/threads/create/', ThreadCreateView.as_view(), name='thread-create'),
    path('my-cabinet/threads/<int:pk>/delete/', ThreadDeleteView.as_view(), name='thread-delete'),
]