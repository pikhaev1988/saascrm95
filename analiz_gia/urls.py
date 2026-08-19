"""
URL configuration for analiz_gia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

admin.site.site_header = "Администрирование Анализ ГИА"
admin.site.site_title = "Анализ ГИА"
admin.site.index_title = "Панель управления"

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(url=f"{settings.STATIC_URL}img/favicon.ico", permanent=True),
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("users.urls")),
    path("api/", include("organizations.urls")),
    path("api/", include("exams.urls")),
    path("api/", include("uploads.urls")),
    path("cabinet/vpr/", include("apps.vpr.urls")),
    path("", include("users.web_urls")),
    path("", include("analytics.urls")),
]

if settings.SERVE_MEDIA_FROM_DJANGO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
