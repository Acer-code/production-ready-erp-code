from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('erp/', include('erp.urls')),
    path('director/', include('erp.urls_director')),
    path('vendor/', include('erp.urls_dealer')),
    path('service/',include('services.urls')),
    path('notifications/', include('notifications.urls')),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
