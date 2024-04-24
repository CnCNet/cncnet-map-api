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
from kirovy.services.cnc_gen_2_services import CncGen2MapParser
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

        new_map = cnc_map.CncMap(
            map_name=map_parser.parser.get(map_parser.map_sections.BASIC, "Name"),
            cnc_game=game,
            is_published=False,
            incomplete_upload=True,
            cnc_user=request.user,
        )
        new_map.save()
        # TODO: Map categories
        # TODO: Save the in memory file object.
        new_map_file = cnc_map.CncMapFile(
            width=map_parser.parser.get(map_parser.map_sections.HEADER, "Width"),
            height=map_parser.parser.get(map_parser.map_sections.HEADER, "Height"),
            name="",  # TODO: Make filename
            cnc_map=new_map,
            file=uploaded_file,
            file_extension=extension,
            cnc_game=new_map.cnc_game,
        )
        new_map_file.save()

        return KirovyResponse(
            t.ResponseData(message="File uploaded successfully"),
            status=status.HTTP_201_CREATED,
        )
