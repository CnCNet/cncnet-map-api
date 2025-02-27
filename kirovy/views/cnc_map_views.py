import io
import logging
import pathlib

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

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


class MapListCreateView(base_views.KirovyListCreateView):
    """
    The view for maps.
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
            Q(Q(is_published=True) | Q(is_legacy=True) | Q(is_temporary=True))
            & Q(is_banned=False)
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
            raise PermissionDenied(
                "cannot-delete-legacy-maps", status.HTTP_403_FORBIDDEN
            )
        return super().perform_destroy(instance)


class MapFileUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.CanUpload]

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        game = CncGame.objects.get(id=request.data["game_id"])
        uploaded_file: UploadedFile = request.data["file"]
        extension = CncFileExtension.objects.get(
            extension=pathlib.Path(uploaded_file.name).suffix.lstrip(".")
        )
        max_size = file_utils.ByteSized(mega=25)
        uploaded_size = file_utils.ByteSized(uploaded_file.size)

        if uploaded_size > max_size:
            return KirovyResponse(
                t.ErrorResponseData(
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
                t.ErrorResponseData(message="Invalid Map File"),
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
            django_image = InMemoryUploadedFile(
                image_io, None, "temp.jpg", "image/jpeg", image_io.tell(), None
            )
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
            t.ResponseData(
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
