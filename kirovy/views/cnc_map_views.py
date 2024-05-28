import io
import logging
import pathlib

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

from kirovy import permissions, typing as t, exceptions, constants
from kirovy.models import MapCategory, cnc_map, CncGame, CncFileExtension
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
    ...


class MapDeleteView(base_views.KirovyDestroyView):
    ...


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
        for game_mode in map_parser.ini.categories:
            category = MapCategory.objects.filter(name__iexact=game_mode).first()
            if not category:
                continue
            new_map.categories.add(category)

        # TODO: Save the preview image and get the link for the return.
        # TODO: Save file hashes.
        new_map_file = cnc_map.CncMapFile(
            width=map_parser.ini.get(CncGen2MapSections.HEADER, "Width"),
            height=map_parser.ini.get(CncGen2MapSections.HEADER, "Height"),
            name=new_map.generate_versioned_name_for_file(),
            cnc_map=new_map,
            file=uploaded_file,
            file_extension=extension,
            cnc_game=new_map.cnc_game,
        )
        new_map_file.save()

        # TODO: Actually serialize the return data and include the link to the preview.
        # TODO: Should probably convert this to DRF for that step.
        return KirovyResponse(
            t.ResponseData(
                message="File uploaded successfully",
                result={
                    "cnc_map": new_map.map_name,
                    "cnc_map_file": new_map_file.file.name,
                    "cnc_map_id": new_map.id,
                },
            ),
            status=status.HTTP_201_CREATED,
        )
