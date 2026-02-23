"""
URL configuration for superapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django_superapp.urls import extend_with_superapp_urlpatterns
from django.urls import include, path
from django.http import HttpResponse, JsonResponse


def health_check(request):
    """Liveness check - verifies DB and Redis are reachable."""
    errors = {}

    # Check database
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        errors["database"] = str(e)

    # Check Redis
    try:
        from django.core.cache import cache
        cache.set("_health_check", "ok", 10)
        if cache.get("_health_check") != "ok":
            errors["redis"] = "cache read/write failed"
    except Exception as e:
        errors["redis"] = str(e)

    if errors:
        return JsonResponse({"status": "unhealthy", "errors": errors}, status=503)

    return HttpResponse("OK", status=200)


def readiness_check(request):
    """Readiness check - lightweight, just confirms the process is responding."""
    return HttpResponse("OK", status=200)


urlpatterns = [
    path("health/", health_check, name="health"),
    path("ready/", readiness_check, name="ready"),
    path("__debug__/", include("debug_toolbar.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from . import apps as superapp_apps
extend_with_superapp_urlpatterns(
    main_urlpatterns=urlpatterns,
    superapp_apps=superapp_apps
)
