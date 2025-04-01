"""
URL configuration for well_patient project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView


urlpatterns = [

    path('wellpatient/', include("patients.urls")),
     path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path('admin/', admin.site.urls),
]

# Serve static and media files during development
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)