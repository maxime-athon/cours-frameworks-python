from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/etudiants/', permanent=True)),
    path('admin/', admin.site.urls),
    path('etudiants/', include('etudiants.urls', namespace='etudiants')),
    path('api/v1/etudiants/', include('etudiants.api_urls')),
    path('auth/', include('auth_api.urls', namespace='auth')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   