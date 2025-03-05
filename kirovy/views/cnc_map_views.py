import io
import logging
import pathlib

from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from django_filters import rest_framework as filters

import kirovy.objects.ui_objects
from kirovy import permissions, typing as t, exceptions, constants
from kirovy.models import (
    MapCategory,
    cnc_map,
    CncGame,
    CncFileExtension,
    map_preview,
    CncMap,
)
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.serializers import cnc_map_serializers
from kirovy.services.cnc_gen_2_services import CncGen2MapParser, CncGen2MapSections
from kirovy.utils import file_utils
from kirovy.views import base_views


_LOGGER = logging.getLogger(__name__)


class MapCategoryListCreateView(base_views.KirovyListCreateView):
    permission_classes = [permissions.IsAdmin | permissions.ReadOnly]
    serializer_class = cnc_map_serializers.MapCategorySerializer
    queryset = MapCategory.objects.all()


class MapListFilters(filters.FilterSet):
    """The filters for the map list endpoint.

    `Docs on how these work <https://django-filter.readthedocs.io/en/stable/guide/rest_framework.html>`_
    """

    include_edits = filters.BooleanFilter(field_name="parent_id", method="filter_include_map_edits")
    # include_maps_from_sub_games = filters.BooleanFilter(
    #     field_name="cnc_game__parent_id", method="filter_include_maps_from_sub_games"
    # )
    cnc_game = filters.ModelMultipleChoiceFilter(
        field_name="cnc_game__id", to_field_name="id", queryset=CncGame.objects.filter(is_visible=True)
    )
    categories = filters.ModelMultipleChoiceFilter(MapCategory.objects.filter())

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
        MapListFilters,
    ]

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


class MapFileUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.CanUpload]

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        game = CncGame.objects.get(id=request.data["game_id"])
        uploaded_file: UploadedFile = request.data["file"]
        extension = CncFileExtension.objects.get(extension=pathlib.Path(uploaded_file.name).suffix.lstrip("."))
        max_size = file_utils.ByteSized(mega=25)
        uploaded_size = file_utils.ByteSized(uploaded_file.size)

        if uploaded_size > max_size:
            return KirovyResponse(
                kirovy.objects.ui_objects.ErrorResponseData(
                    message="File too large",
                    additional={
                        "max_bytes": str(max_size),
                        "your_bytes": str(uploaded_file),
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # TODO: Finish the map upload.
            map_parser = CncGen2MapParser(uploaded_file)
        except exceptions.InvalidMapFile as e:
            return KirovyResponse(
                kirovy.objects.ui_objects.ErrorResponseData(message="Invalid Map File"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        parent: t.Optional[cnc_map.CncMap] = None
        cnc_map_id: t.Optional[str] = map_parser.ini.get(
            constants.CNCNET_INI_SECTION, constants.CNCNET_INI_MAP_ID_KEY, fallback=None
        )
        if cnc_map_id:
            parent = cnc_map.CncMap.objects.filter(id=cnc_map_id).first()

        new_map = cnc_map.CncMap(
            map_name=map_parser.ini.map_name,
            cnc_game=game,
            is_published=False,
            incomplete_upload=True,
            cnc_user=request.user,
            parent=parent,
        )
        new_map.save()

        cnc_net_ini = {constants.CNCNET_INI_MAP_ID_KEY: str(new_map.id)}
        if parent:
            cnc_net_ini[constants.CNCNET_INI_PARENT_ID_KEY] = str(parent.id)

        map_parser.ini[constants.CNCNET_INI_SECTION] = cnc_net_ini

        # Write the modified ini to the uploaded file before we save it to its final location.
        written_ini = io.StringIO()  # configparser doesn't like
        map_parser.ini.write(written_ini)
        written_ini.seek(0)
        uploaded_file.seek(0)
        uploaded_file.truncate()
        uploaded_file.write(written_ini.read().encode("utf8"))

        # Add categories.
        non_existing_categories: t.Set[str] = set()
        for game_mode in map_parser.ini.categories:
            category = MapCategory.objects.filter(name__iexact=game_mode).first()
            if not category:
                non_existing_categories.add(game_mode)
                continue
            new_map.categories.add(category)

        if non_existing_categories:
            _LOGGER.warning(
                "User attempted to upload map with categories that don't exist: non_existing_categories=%s",
                non_existing_categories,
            )

        new_map_file = cnc_map.CncMapFile(
            width=map_parser.ini.get(CncGen2MapSections.HEADER, "Width"),
            height=map_parser.ini.get(CncGen2MapSections.HEADER, "Height"),
            cnc_map=new_map,
            file=uploaded_file,
            file_extension=extension,
            cnc_game=new_map.cnc_game,
        )
        new_map_file.save()

        extracted_image = map_parser.extract_preview()
        extracted_image_url: str = ""
        if extracted_image:
            image_io = io.BytesIO()
            image_extension = CncFileExtension.objects.get(extension="jpg")
            extracted_image.save(image_io, format="JPEG", quality=95)
            django_image = InMemoryUploadedFile(image_io, None, "temp.jpg", "image/jpeg", image_io.tell(), None)
            new_map_preview = map_preview.MapPreview(
                is_extracted=True,
                cnc_map_file=new_map_file,
                file=django_image,
                file_extension=image_extension,
            )
            new_map_preview.save()
            extracted_image_url = new_map_preview.file.url

        # TODO: Actually serialize the return data and include the link to the preview.
        # TODO: Should probably convert this to DRF for that step.
        return KirovyResponse(
            kirovy.objects.ui_objects.ResultResponseData(
                message="File uploaded successfully",
                result={
                    "cnc_map": new_map.map_name,
                    "cnc_map_file": new_map_file.file.url,
                    "cnc_map_id": new_map.id,
                    "extracted_preview_file": extracted_image_url,
                },
            ),
            status=status.HTTP_201_CREATED,
        )
