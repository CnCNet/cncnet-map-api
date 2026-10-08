import datetime
import pathlib
from uuid import UUID

from django.conf import settings
from django.db.models import Q, QuerySet, OuterRef, Subquery, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters import rest_framework as filters
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer

from kirovy import permissions, typing as t
from kirovy.models import (
    MapCategory,
    CncGame,
    CncMap,
    CncMapFile,
)
from kirovy.models.cnc_map import CncMapDownloadStat
from kirovy.objects import ui_objects
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.serializers import cnc_map_serializers
from kirovy.views import base_views
from structlog import get_logger

from kirovy.views.base_views import KirovyApiView

_LOGGER = get_logger(__name__)


def get_maps_visible_to_request(request: KirovyRequest) -> QuerySet[CncMap]:
    """Get the maps that the requesting user is allowed to view or download.

    Who can view what:

        -   Staff: can view everything
        -   Anyone: Can view published, legacy, or temporary (cncnet client uploaded) maps.
            Banned maps will be excluded.
        -   Registered Users: Can view their own maps even if the map is banned.

    :param request:
        The current request.
    :return:
        The maps that the user is allowed to see.
    """
    if request.user.is_staff:
        # Staff users can see everything.
        return CncMap.objects.filter()

    # Anyone can view legacy maps, temporary maps (cncnet client uploads) and published maps that aren't banned.
    queryset: QuerySet[CncMap] = CncMap.objects.filter(
        Q(Q(is_published=True) | Q(is_legacy=True) | Q(is_temporary=True)) & Q(is_banned=False)
    )

    if request.user.is_authenticated:
        # Users can view their own maps in addition to the normal set.
        # User can view their own maps even if the map was banned.
        return queryset | CncMap.objects.filter(cnc_user_id=request.user.id)

    return queryset


def annotate_latest_map_file(queryset: QuerySet[CncMap]) -> QuerySet[CncMap]:
    """Annotate maps with info from their newest map file version.

    Adds ``latest_file_created``, ``latest_file_width``, and ``latest_file_height``.
    Uses subqueries, rather than joins, so that maps with many versions don't show up multiple times
    and don't skew the other aggregates.

    Safe to call more than once on the same queryset.
    """
    if "latest_file_created" in queryset.query.annotations:
        return queryset

    latest_file = CncMapFile.objects.filter(cnc_map_id=OuterRef("pk")).order_by("-version")
    return queryset.annotate(
        latest_file_created=Subquery(latest_file.values("created")[:1]),
        latest_file_width=Subquery(latest_file.values("width")[:1]),
        latest_file_height=Subquery(latest_file.values("height")[:1]),
    )


def annotate_trending_download_count(
    queryset: QuerySet[CncMap], window_days: int | None = None, today: datetime.date | None = None
) -> QuerySet[CncMap]:
    """Annotate maps with ``trending_download_count``, the downloads within the trending window.

    Safe to call more than once on the same queryset.

    :param queryset:
        The maps to annotate.
    :param window_days:
        How many days, including today, count toward the trending score.
        Defaults to :attr:`~kirovy.settings._base.MAP_TRENDING_WINDOW_DAYS`.
    :param today:
        Override "today" for tests. Defaults to today in UTC.
    """
    if "trending_download_count" in queryset.query.annotations:
        return queryset

    window_days = window_days or settings.MAP_TRENDING_WINDOW_DAYS
    today = today or timezone.now().date()
    window_start = today - datetime.timedelta(days=window_days - 1)
    downloads_in_window = (
        CncMapDownloadStat.objects.filter(cnc_map_id=OuterRef("pk"), date__gte=window_start)
        .order_by()
        .values("cnc_map_id")
        .annotate(total=Sum("download_count"))
        .values("total")
    )
    return queryset.annotate(
        trending_download_count=Coalesce(
            Subquery(downloads_in_window, output_field=IntegerField()), Value(0), output_field=IntegerField()
        )
    )


class MapCategoryListCreateView(base_views.KirovyListCreateView):
    """Endpoint to list available map categories, or create a new category."""

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
    game_slug = filters.CharFilter(field_name="cnc_game__slug")

    category_slug = filters.ModelMultipleChoiceFilter(
        field_name="categories__slug", to_field_name="slug", queryset=MapCategory.objects.all()
    )
    """attr: Filter by category (game mode) slug, e.g. ``?category_slug=standard&category_slug=koth``.

    Matches maps that have **any** of the given categories, the same as ``categories``.
    """

    cnc_user_id = filters.UUIDFilter(field_name="cnc_user_id")
    """attr: Only show maps uploaded by this Kirovy user."""

    author = filters.CharFilter(field_name="cnc_user__username", lookup_expr="iexact")
    """attr: Only show maps uploaded by the CnCNet user with this username. Case-insensitive."""

    min_width = filters.NumberFilter(method="filter_latest_file_size")
    max_width = filters.NumberFilter(method="filter_latest_file_size")
    min_height = filters.NumberFilter(method="filter_latest_file_size")
    max_height = filters.NumberFilter(method="filter_latest_file_size")
    """attr: Map size filters, in cells. Checked against the newest version of the map file.

    Maps uploaded by legacy clients don't have their size parsed, so they are excluded by any size filter.
    """

    created_after = filters.IsoDateTimeFilter(field_name="created", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created", lookup_expr="lte")

    _SIZE_FILTER_LOOKUPS: t.ClassVar[t.Dict[str, str]] = {
        "min_width": "latest_file_width__gte",
        "max_width": "latest_file_width__lte",
        "min_height": "latest_file_height__gte",
        "max_height": "latest_file_height__lte",
    }

    class Meta:
        model = CncMap
        fields = ["is_legacy", "is_reviewed", "parent", "categories"]

    def filter_latest_file_size(self, queryset: QuerySet[CncMap], name: str, value: int) -> QuerySet[CncMap]:
        """Filter maps by the width / height of their newest map file."""
        if value is None:
            return queryset
        queryset = annotate_latest_map_file(queryset)
        return queryset.filter(**{self._SIZE_FILTER_LOOKUPS[name]: value})

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


class MapOrderingFilter(OrderingFilter):
    """Ordering for the map browser.

    Supports the regular DRF syntax, e.g. ``?ordering=-download_count,map_name``, plus some
    aliases for the map browser's sort dropdown:

    - ``popular``: most downloads of all time.
    - ``trending``: most downloads within :attr:`~kirovy.settings._base.MAP_TRENDING_WINDOW_DAYS`.
    - ``newest``: newest maps first.
    - ``updated``: maps with the most recently uploaded file version first.

    The annotations needed for the computed orderings are only added when they're requested,
    and ``id`` is always appended as a tie-breaker so that pagination is stable.
    """

    ORDERING_ALIASES: t.ClassVar[t.Dict[str, t.List[str]]] = {
        "popular": ["-download_count", "-created"],
        "trending": ["-trending_download_count", "-download_count", "-created"],
        "newest": ["-created"],
        "updated": ["-latest_file_created", "-created"],
    }

    _LATEST_FILE_FIELDS: t.ClassVar[t.Set[str]] = {"latest_file_created", "latest_file_width", "latest_file_height"}

    def get_ordering(self, request, queryset, view) -> t.List[str] | None:
        params = request.query_params.get(self.ordering_param)
        if params:
            fields: t.List[str] = []
            for param in params.split(","):
                param = param.strip()
                fields.extend(self.ORDERING_ALIASES.get(param, [param]))
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        return self.get_default_ordering(view)

    def filter_queryset(self, request, queryset: QuerySet[CncMap], view) -> QuerySet[CncMap]:
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        ordered_names = {term.lstrip("-") for term in ordering}
        if ordered_names & self._LATEST_FILE_FIELDS:
            queryset = annotate_latest_map_file(queryset)
        if "trending_download_count" in ordered_names:
            queryset = annotate_trending_download_count(queryset)

        if "id" not in ordered_names:
            ordering = [*ordering, "id"]

        return queryset.order_by(*ordering)


class MapListView(base_views.KirovyListCreateView):
    """
    The view for maps.

    Filtering is defined in :class:`~kirovy.views.cnc_map_views.MapListFilters`,
    sorting is defined in :class:`~kirovy.views.cnc_map_views.MapOrderingFilter`.
    """

    http_method_names = ["get"]

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
                Q(is_banned=False, is_published=True, incomplete_upload=False, is_temporary=False)
                | Q(is_legacy=True)
                | Q(is_mapdb1_compatible=True)
            ).filter(cnc_game__is_visible=True)
            # Prefetch data necessary to the map grid. Pre-fetching avoids hitting the database in a loop.
            .select_related("cnc_user", "cnc_game", "parent", "parent__cnc_user")
            # Prefetch the categories because they're displayed like tags.
            # TODO: Since the category list is going to be somewhat small,
            #  maybe the UI should just cache them and I return IDs instead of objects?
            .prefetch_related("categories", "cncmapfile_set", "cncmapimagefile_set")
        )
        return base_query

    filter_backends = [
        filters.DjangoFilterBackend,  # filter first to reduce the count of rows that we full text search on.
        SearchFilter,
        MapOrderingFilter,
    ]
    filterset_class = MapListFilters

    search_param = "search"
    """attr: The query param to use in the URL

     Searches the fields defined in :attr:`~kirovy.views.cnc_map_views.MapListView`
     """

    search_fields = [
        "map_name",
        "^description",
    ]
    """
    attr: Fields that can be text searched using query params.
    `Django REST Framework docs <https://www.django-rest-framework.org/api-guide/filtering/#searchfilter>`_.
    `Built-in django search docs <https://docs.djangoproject.com/en/4.2/ref/contrib/postgres/search/>`_.
    """

    ordering_fields = [
        "map_name",
        "created",
        "modified",
        "download_count",  # "popular"
        "trending_download_count",  # "trending", annotated by MapOrderingFilter.
        "latest_file_created",  # For finding maps with new file versions. Annotated by MapOrderingFilter.
        "latest_file_width",
        "latest_file_height",
        "id",
    ]
    """
    attr: The fields we will sort ordering by.
    `Docs <https://www.django-rest-framework.org/api-guide/filtering/#orderingfilter>`_

    Aliases like ``?ordering=trending`` are defined in :attr:`MapOrderingFilter.ORDERING_ALIASES`.
    """

    ordering = ["-created"]
    """attr: Newest maps first if the UI doesn't specify an ordering."""

    serializer_class = cnc_map_serializers.CncMapBaseSerializer


class MapRetrieveUpdateView(base_views.KirovyRetrieveUpdateView):
    serializer_class = cnc_map_serializers.CncMapBaseSerializer

    def get_queryset(self) -> QuerySet[CncMap]:
        """Get the queryset for map detail views.

        Who can view what:

            -   Staff: can view and edit everything
            -   Anyone: Can view published, legacy, or temporary (cncnet client uploaded) maps.
                Banned maps will be excluded.
            -   Registered Users: Can edit their own maps if the map isn't banned.
                Can view their own maps even if the map is banned.
                The queryset will return a user's banned map, but :class:`kirovy.permissions.CanEdit` will block
                any modification attempts.

        Editing permissions are controlled via :class:`kirovy.permissions.CanEdit`.
        The fields that can be edited are controlled by
        :attr:`kirovy.serializers.cnc_map_serializers.CncMapBaseSerializer.Meta.editable_fields`.

        View permissions are controlled via :class:`kirovy.permissions.ReadOnly`.

        :return:
        """
        return get_maps_visible_to_request(self.request)

    def perform_update(self, serializer: cnc_map_serializers.CncMapBaseSerializer) -> None:
        """Save the edit and keep a moderation trail when staff edit someone else's map."""
        user = self.request.user
        cnc_map: CncMap = serializer.instance
        is_moderator_edit = user.is_staff and cnc_map.cnc_user_id != user.id
        changed_fields = sorted(serializer.validated_data.keys())

        serializer.save(last_modified_by=user)

        if is_moderator_edit:
            cnc_map.record_moderator_action(user, "Edited", f"fields: {', '.join(changed_fields)}")


class MapDownloadView(KirovyApiView):
    """Download a map file and count the download for the map browser's popular / trending sorting.

    ``GET /maps/<map_id>/download/`` returns the newest version of the map file.
    ``GET /maps/<map_id>/download/?version=2`` returns a specific version.

    Visibility follows the map detail endpoint: banned maps are only downloadable by their owner and staff.
    """

    permission_classes = [AllowAny]

    def get(self, request: KirovyRequest, pk: UUID, format=None) -> FileResponse:
        cnc_map: CncMap | None = get_maps_visible_to_request(request).filter(id=pk).first()
        if not cnc_map:
            raise NotFound("map-not-found")

        map_files = CncMapFile.objects.filter(cnc_map_id=cnc_map.id)
        version = request.query_params.get("version")
        if version:
            if not version.isdigit():
                raise NotFound("map-version-not-found")
            map_file = map_files.filter(version=int(version)).first()
        else:
            map_file = map_files.order_by("-version").first()

        if not map_file:
            raise NotFound("map-version-not-found")

        cnc_map.record_download()

        return FileResponse(
            map_file.file.open("rb"), as_attachment=True, filename=pathlib.Path(map_file.file.name).name
        )


class MapDeleteView(base_views.KirovyDestroyView):
    queryset = CncMap.objects.filter()

    def perform_destroy(self, instance: CncMap):
        if instance.is_legacy:
            raise PermissionDenied("cannot-delete-legacy-maps", status.HTTP_403_FORBIDDEN)
        return super().perform_destroy(instance)


class BackwardsCompatibleMapView(KirovyApiView):
    """Match the legacy mapdb download endpoints.

    This is needed until the new UI is running for the clients CnCNet owns.

    This will need to be kept around so that we maintain support for the clients that
    we don't have the source code for.

    The backwards compatible URL is ``/{game_slug}/{map_hash_sha1}``
    """

    permission_classes = [AllowAny]

    def get(self, request, sha1_hash_filename: str, game_id: UUID, format=None):
        """
        Return the map matching the hash, if it exists.
        """
        sha1_hash = pathlib.Path(sha1_hash_filename).stem
        _LOGGER.debug("Attempted backwards compatible download", av={"sha1": sha1_hash, "game": str(game_id)})
        map_file = CncMapFile.objects.find_legacy_map_by_sha1(sha1_hash, game_id)
        if not map_file or map_file.cnc_map.is_banned:
            # Banned maps (e.g. cheat maps shared in lobbies) must not be served to legacy clients either.
            return KirovyResponse(status=status.HTTP_404_NOT_FOUND)

        map_file.cnc_map.record_download()

        return FileResponse(map_file.file.open("rb"), as_attachment=True, filename=f"{map_file.hash_sha1}.zip")


class MapLegacyStaticUI(KirovyApiView):
    """Temporary upload page for backwards compatible upload testing.

    Map authors need an easy way to upload their maps to the database so that they
    can debug a failed client upload.

    This should be deprecated once the new UI is fully up and running.
    (Or move it to a more django-friendly endpoint and give it space in the nw UI.)

    Emulates `the legacy uploader <https://mapdb.cncnet.org/upload-manual.html>`_
    """

    permission_classes = [AllowAny]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "map_legacy_upload_ui.html"

    def get(self, request: KirovyRequest) -> KirovyResponse:
        return KirovyResponse()


class MapLegacySearchUI(MapListView):

    permission_classes = [AllowAny]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "legacy_search.html"
    pagination_class = None

    # TODO: Require filters.
    def get(self, request, *args, **kwargs) -> KirovyResponse[ui_objects.ListResponseData | None]:
        if not request.query_params.get("game_slug"):
            return KirovyResponse[None](status=status.HTTP_200_OK)
        response = super().get(request, *args, **kwargs)
        return response
