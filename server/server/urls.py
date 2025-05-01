# server/procurement_platform/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('aadf.urls')),  # API endpoints
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site headers
admin.site.site_header = "AADF Procurement Platform Admin"
admin.site.site_title = "AADF Procurement Admin Portal"
admin.site.index_title = "Welcome to AADF Procurement Platform"