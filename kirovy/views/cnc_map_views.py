import hashlib
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
from kirovy.objects.ui_objects import ErrorResponseData
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


class MapHashes(t.NamedTuple):
    md5: str
    sha1: str
    sha512: str


class MapFileUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.CanUpload]
    request: KirovyRequest

    @staticmethod
    def _get_map_hashes(uploaded_file: UploadedFile) -> MapHashes:
        file_contents = uploaded_file.read()
        map_hash_sha512 = hashlib.sha512(file_contents).hexdigest()
        map_hash_md5 = hashlib.md5(file_contents).hexdigest()
        map_hash_sha1 = hashlib.sha1().hexdigest()  # legacy ban list support

        return MapHashes(md5=map_hash_md5, sha1=map_hash_sha1, sha512=map_hash_sha512)

    def validate_map_file(self, uploaded_file: UploadedFile, hashes: MapHashes) -> t.Tuple[bool, t.Optional[str]]:
        matched_hashes = cnc_map.CncMapFile.objects.filter(
            Q(hash_md5=hashes.md5) | Q(hash_sha512=hashes.sha512)
        ).prefetch_related("cnc_map")

        if not matched_hashes:
            return True, None

        is_banned = next(iter([x for x in matched_hashes if x.cnc_map.is_banned]))

        if is_banned:
            naughty_ip_address = self.request.META.get("HTTP_X_FORWARDED_FOR", "unknown")
            user = self.request.user

            log_attrs = {
                "ip_address": naughty_ip_address,
                "user": f"[{user.cncnet_id}] {user.username}" if user else "unauthenticated_upload",
                "map_file_id": is_banned.id,
                "map_id": is_banned.cnc_map.id,
            }

            _LOGGER.info("attempted_uploading_banned_map_file", log_attrs)

        return False, "duplicate-file"

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        # todo: add file version support.
        # todo: make validation less trash
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

        map_hashes = self._get_map_hashes(uploaded_file)
        valid, validation_message = self.validate_map_file(uploaded_file, map_hashes)
        if not valid:
            return KirovyResponse(
                data=ErrorResponseData(message=validation_message), status=status.HTTP_400_BAD_REQUEST
            )

        try:
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
            hash_md5=map_hashes.md5,
            hash_sha512=map_hashes.sha512,
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
