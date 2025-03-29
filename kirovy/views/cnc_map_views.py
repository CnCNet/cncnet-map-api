import pathlib
from uuid import UUID

from django.db.models import Q, QuerySet
from django.http import FileResponse
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters import rest_framework as filters
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from kirovy import permissions
from kirovy.models import (
    MapCategory,
    CncGame,
    CncMap,
    CncMapFile,
)
from kirovy.response import KirovyResponse
from kirovy.serializers import cnc_map_serializers
from kirovy.views import base_views
from structlog import get_logger


_LOGGER = get_logger(__name__)


class MapCategoryListCreateView(base_views.KirovyListCreateView):
    permission_classes = [permissions.IsAdmin | permissions.ReadOnly]
    serializer_class = cnc_map_serializers.MapCategorySerializer
    queryset = MapCategory.objects.all()


class MapListFilters(filters.FilterSet):
    """The filters for the map list endpoint.

    `Docs on how these work <https://django-filter.readthedocs.io/en/stable/guide/rest_framework.html>`_

    For the Many-to-Many filters, like categories, refer to the
    `MultipleChoiceFilterDocs <https://django-filter.readthedocs.io/en/stable/ref/filters.html#multiplechoicefilter>_`.

    The TL;DR is that multiple choices are done by specifying the same field multiple times.

    e.g. ``/maps/search/?categories=1&categories=2&categories=3``
    """

    include_edits = filters.BooleanFilter(field_name="parent_id", method="filter_include_map_edits")
    # include_maps_from_sub_games = filters.BooleanFilter(
    #     field_name="cnc_game__parent_id", method="filter_include_maps_from_sub_games"
    # )
    cnc_game = filters.ModelMultipleChoiceFilter(
        field_name="cnc_game__id", to_field_name="id", queryset=CncGame.objects.filter(is_visible=True)
    )
    # categories = filters.ModelMultipleChoiceFilter(queryset=MapCategory.objects.filter())

    class Meta:
        model = CncMap
        fields = ["is_legacy", "is_reviewed", "parent", "categories"]

    def filter_include_map_edits(self, queryset: QuerySet[CncMap], name: str, value: bool) -> QuerySet[CncMap]:
        """We will exclude maps that are edits of other maps by default.

        If ``value`` is true, then we will return edits of other maps.
        Maps with ``parent_id IS NOT NULL`` are edits of another map.

        See: :attr:`kirovy.models.cnc_map.CncMap.parent`.

        :param queryset:
            The queryset that we will modify with our filters.
        :param name:
            The name of the field. We don't use it, but it's required for the interface.
        :param value:
            The value from the UI. If ``True``, then we will include map edits.
        :return:
            The queryset, maybe modified to include map edits.
        """
        if not value:
            # Was not provided, or set to false. Don't include map edits.
            return queryset.exclude(parent_id__isnull=False)

        return queryset

    # TODO: Does anyone even want this behavior?
    # def filter_include_maps_from_sub_games(
    #     self, queryset: QuerySet[CncMap], name: str, value: bool
    # ) -> QuerySet[CncMap]:
    #     """We will exclude maps that are for sub games of the selected games by default.
    #
    #     If ``value`` is true, then we will return maps for sub games.
    #     e.g. return Yuri's Revenge maps if game is Red Alert 2.
    #
    #     Sub games can also be mods, according to the database, so make sure to set the filter for including mods
    #     too.
    #
    #     See: :attr:`kirovy.models.cnc_game.CncGame.parent_game`.
    #
    #     :param queryset:
    #         The queryset that we will modify with our filters.
    #     :param name:
    #         The name of the field. We don't use it, but it's required for the interface.
    #     :param value:
    #         The value from the UI. If ``True``, then we will include maps for sub games of the game filter.
    #     :return:
    #         The queryset, maybe modified to include maps for sub games.
    #     """
    #     specified_games = self.data["cnc_game"]
    #     if not specified_games:
    #         # The user didn't specify a game, so don't perform any modifications to the query.
    #         return queryset
    #     if not value:
    #         # User provided games, but does not want to see sub games.
    #         return queryset.exclude(cnc_game__parent_game_id__isnull=False)
    #
    #     # User wants to see sub games
    #     return queryset | CncMap.objects.filter(cnc_game__parent_game__in=)


class MapListCreateView(base_views.KirovyListCreateView):
    """
    The view for maps.
    """

    def get_queryset(self):
        """The default query from which all other map list queries are built.

        By default, maps will be shown if (they are published, and not banned) or if they're a legacy map.

        We only show maps for games that are visible (so we can hide Generals until it's done.)

        .. code-block:: python

            ```CncMap.objects.filter(Q(x=y, z=a) | Q(a=b))```

        Translates to:

        .. code-block:: sql

            SELECT * FROM cnc_maps WHERE (x=y AND z=a) OR a=b

        """
        base_query = (
            CncMap.objects.filter(
                Q(is_banned=False, is_published=True, incomplete_upload=False, is_temporary=False) | Q(is_legacy=True)
            ).filter(cnc_game__is_visible=True)
            # Prefetch data necessary to the map grid. Pre-fetching avoids hitting the database in a loop.
            .select_related("cnc_user", "cnc_game", "parent", "parent__cnc_user")
            # Prefetch the categories because they're displayed like tags.
            # TODO: Since the category list is going to be somewhat small,
            #  maybe the UI should just cache them and I return IDs instead of objects?
            .prefetch_related("categories")
        )
        return base_query

    filter_backends = [
        SearchFilter,
        OrderingFilter,
        filters.DjangoFilterBackend,
    ]
    filterset_class = MapListFilters

    search_fields = [
        "@map_name",
        "^description",
    ]
    """
    attr: Fields that can be text searched using query params.
    `Django REST Framework docs <https://www.django-rest-framework.org/api-guide/filtering/#searchfilter>`_.
    `Built-in django search docs <https://docs.djangoproject.com/en/4.2/ref/contrib/postgres/search/>`_.
    """

    ordering_fields = [
        "map_name",
        "cnc_map_file__created",  # For finding maps with new file versions.
        "cnc_map_file__width",
        "cnc_map_file__height",
    ]
    """
    attr: The fields we will sort ordering by.
    `Docs <https://www.django-rest-framework.org/api-guide/filtering/#orderingfilter>`_
    """

    serializer_class = cnc_map_serializers.CncMapBaseSerializer


class MapRetrieveUpdateView(base_views.KirovyRetrieveUpdateView):
    serializer_class = cnc_map_serializers.CncMapBaseSerializer

    def get_queryset(self):
        """Get the queryset for map detail views.

        Who can view what:

            -   Staff: can view and edit everything
            -   Anyone: Can view published, legacy, or temporary (cncnet client uploaded) maps.
                Banned maps will be excluded.
            -   Registered Users: Can edit their own maps if the map isn't banned.
                Can view their own maps even if the map banned.
                The queryset will return a user's banned map, but :class:`kirovy.permissions.CanEdit` will block
                any modification attempts.

        Editing permissions are controlled via :class:`kirovy.permissions.CanEdit`.

        View permissions are controlled via :class:`kirovy.permissions.ReadOnly`.

        :return:
        """
        if self.request.user.is_staff:
            # Staff users can see everything.
            return CncMap.objects.filter()

        # Anyone can view legacy maps, temporary maps (for the cncnet client,) and published maps that aren't banned.
        queryset = CncMap.objects.filter(
            Q(Q(is_published=True) | Q(is_legacy=True) | Q(is_temporary=True)) & Q(is_banned=False)
        )

        if self.request.user.is_authenticated:
            # Users can view their own maps in addition to the normal set.
            # User can view their own maps even if the map was banned.
            return queryset | CncMap.objects.filter(cnc_user_id=self.request.user.id)

        return queryset


class MapDeleteView(base_views.KirovyDestroyView):
    queryset = CncMap.objects.filter()

    def perform_destroy(self, instance: CncMap):
        if instance.is_legacy:
            raise PermissionDenied("cannot-delete-legacy-maps", status.HTTP_403_FORBIDDEN)
        return super().perform_destroy(instance)


class BackwardsCompatibleMapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sha1_hash_filename: str, game_id: UUID, format=None):
        """
        Return the map matching the hash, if it exists.
        """
        sha1_hash = pathlib.Path(sha1_hash_filename).stem
        _LOGGER.debug("Attempted backwards compatible download", av={"sha1": sha1_hash, "game": str(game_id)})
        map_file = CncMapFile.objects.find_legacy_map_by_sha1(sha1_hash, game_id)
        if not map_file:
            return KirovyResponse(status=status.HTTP_404_NOT_FOUND)

        return FileResponse(map_file.file.open("rb"), as_attachment=True, filename=f"{map_file.hash_sha1}.zip")
