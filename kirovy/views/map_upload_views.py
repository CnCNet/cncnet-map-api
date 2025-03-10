import hashlib
import io
import pathlib
from abc import ABCMeta

from cryptography.utils import cached_property
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.db.models import Q, QuerySet
from rest_framework import status, serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from kirovy import typing as t, permissions, exceptions, constants, logging
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.models import cnc_map, CncGame, CncFileExtension, MapCategory, map_preview
from kirovy.objects.ui_objects import ErrorResponseData, ResultResponseData
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.serializers import cnc_map_serializers
from kirovy.services.cnc_gen_2_services import CncGen2MapParser, CncGen2MapSections
from kirovy.utils import file_utils


_LOGGER = logging.get_logger(__name__)


class MapHashes(t.NamedTuple):
    md5: str
    sha1: str
    sha512: str


class _BaseMapFileUploadView(APIView, metaclass=ABCMeta):
    parser_classes = [MultiPartParser]
    permission_classes: t.ClassVar[t.Iterable[BasePermission]]
    request: KirovyRequest
    upload_is_temporary: t.ClassVar[bool]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        has_permission_class_set = getattr(self, "permission_classes", None)
        if has_permission_class_set is None:
            raise NotImplementedError("Must define permissions to subclass the map uploader.")
        has_upload_is_temporary_set = getattr(self, "upload_is_temporary", None)
        if has_upload_is_temporary_set is None:
            raise NotImplementedError("Must define what this endpoint sets for ``map_file.is_temporary``.")

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        # todo: add file version support.
        # todo: make validation less trash
        uploaded_file: UploadedFile = request.data["file"]

        game_id = self.get_game_id_from_request(request)
        extension_id = self.get_extension_id_for_upload(uploaded_file)
        self.verify_file_size_is_allowed(uploaded_file)

        map_hashes = self._get_file_hashes(uploaded_file)
        self.verify_file_does_not_exist(map_hashes)
        map_parser = self.get_map_parser(uploaded_file)
        parent_map = self.get_map_parent(map_parser)

        # Make the map that we will attach the map file too.
        new_map = cnc_map.CncMap(
            map_name=map_parser.ini.map_name,
            cnc_game_id=game_id,
            is_published=False,
            incomplete_upload=True,
            cnc_user=request.user,
            parent=parent_map,
        )
        new_map.save()

        # Set the cncnet map ID in the map file ini.
        cnc_net_ini = {constants.CNCNET_INI_MAP_ID_KEY: str(new_map.id)}
        if parent_map:
            # If the map has a parent, specify that map's parent so that we can properly credit the original creator.
            cnc_net_ini[constants.CNCNET_INI_MAP_PARENT_ID_KEY] = str(parent_map.id)

        # write the ID(s) to the cncnet section of the INI.
        map_parser.ini[constants.CNCNET_INI_SECTION] = cnc_net_ini

        # Write the modified ini to the uploaded file before we save it to its final location.
        written_ini = io.StringIO()  # configparser doesn't like strings
        map_parser.ini.write(written_ini)
        written_ini.seek(0)
        uploaded_file.seek(0)
        uploaded_file.truncate()
        uploaded_file.write(written_ini.read().encode("utf8"))
        map_hashes_post_processing = self._get_file_hashes(uploaded_file)

        # Add categories.
        # TODO: move above making the new map and put categories in the serializer.
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
                **self.user_log_attrs,
            )

        new_map_file_serializer = cnc_map_serializers.CncMapFileSerializer(
            data=dict(
                width=map_parser.ini.get(CncGen2MapSections.HEADER, "Width"),
                height=map_parser.ini.get(CncGen2MapSections.HEADER, "Height"),
                cnc_map_id=new_map.id,
                file=uploaded_file,
                file_extension_id=extension_id,
                cnc_game_id=new_map.cnc_game_id,
                hash_md5=map_hashes_post_processing.md5,
                hash_sha512=map_hashes_post_processing.sha512,
                hash_sha1=map_hashes_post_processing.sha1,
            ),
            context={"request": self.request},
        )
        new_map_file_serializer.is_valid(raise_exception=True)
        new_map_file = new_map_file_serializer.save()

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

    def get_map_parser(self, uploaded_file: UploadedFile) -> CncGen2MapParser:
        try:
            return CncGen2MapParser(uploaded_file)
        except exceptions.InvalidMapFile as e:
            raise KirovyValidationError(detail=e.message, code=e.code, additional=e.params)

    def get_map_parent(self, map_parser: CncGen2MapParser) -> cnc_map.CncMap | None:
        """Determine if this map has a parent or not.

        This exists to make sure original authors are properly credited when someone uploads an edit of their map.

        # TODO: Support uploading new versions of maps. Will need a new permission class called "CanAddNewVersion".

        :param map_parser:
        :return:
        """
        parent: t.Optional[cnc_map.CncMap] = None
        cnc_map_id: t.Optional[str] = map_parser.ini.get(
            constants.CNCNET_INI_SECTION, constants.CNCNET_INI_MAP_ID_KEY, fallback=None
        )
        if cnc_map_id:
            parent = cnc_map.CncMap.objects.filter(id=cnc_map_id).first()

        return parent

    @cached_property
    def user_log_attrs(self) -> t.DictStrAny:
        # todo move to structlogger
        naughty_ip_address = self.request.META.get("HTTP_X_FORWARDED_FOR", "unknown")
        user = self.request.user
        return {
            "ip_address": naughty_ip_address,
            "user": f"[{user.cncnet_id}] {user.username}" if user else "unauthenticated_upload",
        }

    @staticmethod
    def _get_file_hashes(uploaded_file: UploadedFile) -> MapHashes:
        map_hash_sha512 = file_utils.hash_file_sha512(uploaded_file)
        map_hash_md5 = file_utils.hash_file_md5(uploaded_file)
        map_hash_sha1 = file_utils.hash_file_sha1(uploaded_file)  # legacy ban list support

        return MapHashes(md5=map_hash_md5, sha1=map_hash_sha1, sha512=map_hash_sha512)

    def get_game_id_from_request(self, request: KirovyRequest) -> str | None:
        """Get the game_id from the request.

        This is a method, rather than a direct lookup, so that the client can use ``game_slug``.
        """
        raise NotImplementedError()

    def get_extension_id_for_upload(self, uploaded_file: UploadedFile) -> str:
        uploaded_extension = pathlib.Path(uploaded_file.name).suffix.lstrip(".").lower()
        # iexact is case insensitive
        kirovy_extension = CncFileExtension.objects.filter(
            extension__iexact=uploaded_extension,
            extension_type__in=cnc_map.CncMapFile.ALLOWED_EXTENSION_TYPES,
        ).first()

        if kirovy_extension:
            return str(kirovy_extension.id)

        _LOGGER.warning(
            "User attempted uploading unknown filetype",
            uploaded_extension=uploaded_extension,
            **self.user_log_attrs,  # todo: the userattrs should be a context tag for structlog.
        )
        raise serializers.ValidationError(
            detail=f"'{uploaded_extension}' is not a valid map file extension.",
            code="file-extension-not-supported",
        )

    def verify_file_does_not_exist(self, hashes: MapHashes) -> None:
        """Check to make sure that a map file doesn't exist.

        We check the overall file because we want to allow e.g. a new version of a map to be uploaded
        with fixes to its campaign scripts.

        :param hashes:
            The hashes of the uploaded file.
        :return:
            Nothing
        :raises KirovyValidationError:
            Raised if a duplicate file exists.
        """
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

        raise KirovyValidationError(
            detail="This map file already exists",
            code="duplicate-map",
            additional={"existing_map_id": matched_hashes[0].cnc_map_id},
        )

    def verify_file_size_is_allowed(self, uploaded_file: UploadedFile) -> None:
        """Check that the file is small enough, while also not being empty.

        :param uploaded_file:
            The file from the API.
        :return:
            Nothing. No news is good news.
        :raises KirovyValidationError:
            Raised if the file is too big, or suspiciously small.
        """
        uploaded_size = file_utils.ByteSized(uploaded_file.size)
        if uploaded_size == file_utils.ByteSized(0):
            raise KirovyValidationError(
                detail="The uploaded file is empty",
                code="where-file",
            )
        if uploaded_size > settings.MAX_UPLOADED_FILE_SIZE_MAP:
            raise KirovyValidationError(
                detail="File too large",
                code="file-too-large",
                additional={
                    "max_bytes": str(settings.MAX_UPLOADED_FILE_SIZE_MAP),
                    "your_bytes": str(uploaded_file),
                },
            )


class MapFileUploadView(_BaseMapFileUploadView):
    permission_classes = [permissions.CanUpload]
    upload_is_temporary = False

    def get_game_id_from_request(self, request: KirovyRequest) -> str | None:
        return request.data.get("game_id")
