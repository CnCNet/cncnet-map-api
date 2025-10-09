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
from django.db import connection
from django.urls import path, include, URLPattern, URLResolver
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

import kirovy.views.map_image_views
from kirovy.models import CncGame
from kirovy.settings import settings_constants
from kirovy.views import test, cnc_map_views, permission_views, admin_views, map_upload_views
from kirovy import typing as t, constants

_DjangoPath = URLPattern | URLResolver


def _get_games_url_patterns() -> list[_DjangoPath]:
    """Return URLs compatible with legacy CnCNet clients.

    - URLs are loaded when the :mod:`kirovy.urls` module is loaded, which happens when Django starts.
    - Checking the game slugs requires migration ``0002`` to have been run.

    These conditions caused a crash when running migrations for the first time, so now we return
    nothing if we detect that migrations haven't been run yet.

    .. codeauthor:: rohsyl aka wu-shaolin

    :return:
        A list of URLs that are backwards compatible with MapDB 1.0. Returns an empty list if migrations
        haven't been run yet.
    """

    if "kirovy_cncgame" not in connection.introspection.table_names():
        # This should only ever happen the first time ``manage.py migrate kirovy`` is run.
        return []

    return [
        path("upload-manual", cnc_map_views.MapLegacyStaticUI.as_view()),
        path("upload", map_upload_views.CncNetBackwardsCompatibleUploadView.as_view()),
        path("search", cnc_map_views.MapLegacySearchUI.as_view()),
        *(
            # Make e.g. /yr/map_hash, /ra2/map_hash, etc
            path(
                f"{g.slug}/<str:sha1_hash_filename>",
                cnc_map_views.BackwardsCompatibleMapView.as_view(),
                {"game_id": g.id},
            )
            for g in CncGame.objects.filter(slug__in=constants.BACKWARDS_COMPATIBLE_GAMES)
        ),
    ]


def _get_url_patterns() -> list[_DjangoPath]:
    """Return the root level url patterns.

    I added this because I wanted to have the root URLs at the top of the file,
    but I didn't want to have other url files.
    """
    dev_urls = []
    if settings.RUN_ENVIRONMENT == settings_constants.RunEnvironment.DEVELOPMENT:
        dev_urls = [
            path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
            # Optional UI:
            path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
            path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
        ]

    backwards_compatible_urls = _get_games_url_patterns()

    return (
        [
            path("admin/", include(admin_patterns)),
            path("test/jwt", test.TestJwt.as_view()),
            path("ui-permissions/", permission_views.ListPermissionForAuthUser.as_view()),
            path("maps/", include(map_patterns)),
            # path("users/<uuid:cnc_user_id>/", ...),  # will show which files a user has uploaded.
            # path("games/", ...),  # get games.,
        ]
        + backwards_compatible_urls
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # static assets
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # user uploads
        + dev_urls
    )


# /maps/
map_patterns = [
    # path("categories/", ...),  # return all categories
    # path("categories/game/<uuid:cnc_game_id>/", ...),
    path("categories/", cnc_map_views.MapCategoryListCreateView.as_view()),
    path("upload/", map_upload_views.MapFileUploadView.as_view()),
    path("client/upload/", map_upload_views.CncnetClientMapUploadView.as_view()),
    path("<uuid:pk>/", cnc_map_views.MapRetrieveUpdateView.as_view()),
    path("delete/<uuid:pk>/", cnc_map_views.MapDeleteView.as_view()),
    path("search/", cnc_map_views.MapListView.as_view()),
    path("img/", kirovy.views.map_image_views.MapImageFileUploadView.as_view()),
    # path("img/<uuid:map_id>/", ...),
    # path("search/")
]

# /users/
user_patterns = [
    # path("<uuid:pk>")
]

# /admin/
admin_patterns = [path("ban/", admin_views.BanView.as_view())]

urlpatterns = _get_url_patterns()
