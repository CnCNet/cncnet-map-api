import hashlib
import io
import pathlib

from cryptography.utils import cached_property
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

from kirovy import typing as t, permissions, exceptions, constants, logging
from kirovy.models import cnc_map, CncGame, CncFileExtension, MapCategory, map_preview
from kirovy.objects.ui_objects import ErrorResponseData, ResultResponseData
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.services.cnc_gen_2_services import CncGen2MapParser, CncGen2MapSections
from kirovy.utils import file_utils


_LOGGER = logging.get_logger(__name__)


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

    @cached_property
    def user_log_attrs(self) -> t.DictStrAny:
        # todo move to structlogger
        naughty_ip_address = self.request.META.get("HTTP_X_FORWARDED_FOR", "unknown")
        user = self.request.user
        return {
            "ip_address": naughty_ip_address,
            "user": f"[{user.cncnet_id}] {user.username}" if user else "unauthenticated_upload",
        }

    def check_extension(self, uploaded_file: UploadedFile) -> CncFileExtension | ErrorResponseData:
        uploaded_extension = pathlib.Path(uploaded_file.name).suffix.lstrip(".")
        kirovy_extension = CncFileExtension.objects.filter(extension=uploaded_extension).first()

        if kirovy_extension and kirovy_extension.extension_type == kirovy_extension.ExtensionTypes.MAP:
            return kirovy_extension

        _LOGGER.warning(
            "User attempted uploading unknown filetype",
            uploaded_extension=uploaded_extension,
            **self.user_log_attrs,
        )
        return ErrorResponseData(message="unsupported-file-type", additional={"attempted": uploaded_extension})

    def check_file_hashes(self, hashes: MapHashes) -> ErrorResponseData | None:
        matched_hashes: QuerySet[cnc_map.CncMapFile] = (
            cnc_map.CncMapFile.objects.filter(Q(hash_md5=hashes.md5) | Q(hash_sha512=hashes.sha512))
            .prefetch_related("cnc_map")
            .order_by("created")
            .all()
        )

        if not matched_hashes:
            return None

        is_banned = next(iter([x for x in matched_hashes if x.cnc_map.is_banned]))

        if is_banned:
            log_attrs = {
                **self.user_log_attrs,
                "map_file_id": is_banned.id,
                "map_id": is_banned.cnc_map.id,
            }

            _LOGGER.info("attempted_uploading_banned_map_file", **log_attrs)

        return ErrorResponseData(message="duplicate-map", additional={"existing_map_id": matched_hashes[0].cnc_map_id})

    def check_game(self) -> CncGame | ErrorResponseData:
        game_slug = self.request.data.get("game_slug", None)
        game_id = self.request.data.get("game_id", None)

        if not bool(game_slug) ^ bool(game_id):
            return ErrorResponseData(message="set-game-slug-xor-game-id")

        game = CncGame.objects.filter(id=self.request.data["game_id"]).first()
        if not game:
            return ErrorResponseData(message="game-does-not-exist")

        return game

    def check_file_size(self, uploaded_file: UploadedFile) -> ErrorResponseData | None:
        uploaded_size = file_utils.ByteSized(uploaded_file.size)
        if uploaded_size > settings.MAX_UPLOADED_FILE_SIZE_MAP:
            return ErrorResponseData(
                message="File too large",
                additional={
                    "max_bytes": str(settings.MAX_UPLOADED_FILE_SIZE_MAP),
                    "your_bytes": str(uploaded_file),
                },
            )

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        # todo: add file version support.
        # todo: make validation less trash
        uploaded_file: UploadedFile = request.data["file"]

        game = self.check_game()
        if isinstance(game, ErrorResponseData):
            return KirovyResponse(data=game, status=status.HTTP_400_BAD_REQUEST)

        extension = self.check_extension(uploaded_file)
        if isinstance(extension, ErrorResponseData):  # todo: sloppy. Make a custom error class.
            return KirovyResponse(data=extension, status=status.HTTP_400_BAD_REQUEST)

        if error_data := self.check_file_size(uploaded_file):
            return KirovyResponse(status=status.HTTP_400_BAD_REQUEST, data=error_data)

        map_hashes = self._get_map_hashes(uploaded_file)
        if error_data := self.check_file_hashes(map_hashes):
            return KirovyResponse(status=status.HTTP_400_BAD_REQUEST, data=error_data)

        try:
            map_parser = CncGen2MapParser(uploaded_file)
        except exceptions.InvalidMapFile as e:
            return KirovyResponse(
                ErrorResponseData(message="Invalid Map File"),
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
        written_ini = io.StringIO()  # configparser doesn't like strings
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
            ResultResponseData(
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
