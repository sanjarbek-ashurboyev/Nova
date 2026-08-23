from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('catalog.urls')),
    path('', include('accounts.urls')),
    path('', include('orders.urls')),
    path('operator/', include('operator_app.urls')),
    path('driver/', include('driver_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)