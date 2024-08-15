"""kirovy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.urls import path, include

from kirovy.views import test, cnc_map_views, permission_views
from kirovy import typing as t


def _get_url_patterns() -> t.List[path]:
    """Return the root level url patterns.

    I added this because I wanted to have the root URLs at the top of the file,
    but I didn't want to have other url files.
    """
    return (
        [
            path("admin/", admin.site.urls),
            path("test/jwt", test.TestJwt.as_view()),
            path(
                "ui-permissions/", permission_views.ListPermissionForAuthUser.as_view()
            ),
            path("maps/", include(map_patterns)),
            # path("users/<uuid:cnc_user_id>/", ...),  # will show which files a user has uploaded.
            # path("games/", ...),  # get games.
        ]
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )


map_patterns = [
    # path("categories/", ...),  # return all categories
    # path("categories/game/<uuid:cnc_game_id>/", ...),
    path("categories/", cnc_map_views.MapCategoryListCreateView.as_view()),
    path("upload/", cnc_map_views.MapFileUploadView.as_view()),
    # path("img/")
    # path("<uuid:map_id>/", ...),
    # path("img/<uuid:map_id>/", ...),
    # path("search/")
]


urlpatterns = _get_url_patterns()
