import io
import pathlib
from abc import ABCMeta

from cryptography.utils import cached_property
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile, File
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.db.models import Q, QuerySet
from rest_framework import status, serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission, AllowAny
from rest_framework.views import APIView

from kirovy import typing as t, permissions, exceptions, constants, logging
from kirovy.constants.api_codes import UploadApiCodes
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.models import cnc_map, CncGame, CncFileExtension, MapCategory, map_preview, CncUser
from kirovy.objects.ui_objects import ResultResponseData
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.serializers import cnc_map_serializers
from kirovy.serializers.cnc_map_serializers import CncMapBaseSerializer
from kirovy.services import legacy_upload
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

        game = self.get_game_from_request(request)
        if not game:
            raise KirovyValidationError(detail="Game doesnot exist", code=UploadApiCodes.GAME_DOES_NOT_EXIST)
        extension_id = self.get_extension_id_for_upload(uploaded_file)
        self.verify_file_size_is_allowed(uploaded_file)

        map_hashes = self._get_file_hashes(uploaded_file)
        self.verify_file_does_not_exist(map_hashes)
        map_parser = self.get_map_parser(uploaded_file)
        parent_map = self.get_map_parent(map_parser)

        # Make the map that we will attach the map file too.
        map_serializer = CncMapBaseSerializer(
            data=dict(
                map_name=map_parser.ini.map_name,
                description="",
                cnc_game_id=game.id,
                is_published=False,
                incomplete_upload=True,
                cnc_user_id=request.user.id,
                parent_id=parent_map.id if parent_map else None,
            ),
            context={"request": self.request},
        )
        if not map_serializer.is_valid():
            raise KirovyValidationError(
                "Map failed validation", code=UploadApiCodes.INVALID, additional=map_serializer.errors
            )

        new_map = map_serializer.save()

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
        new_map_file: cnc_map.CncMapFile = new_map_file_serializer.save()

        extracted_image_url = self.extract_preview(new_map_file, map_parser)

        return KirovyResponse(
            ResultResponseData(
                message="File uploaded successfully",
                result={
                    "cnc_map": new_map.map_name,
                    "cnc_map_file": new_map_file.file.url,
                    "cnc_map_id": new_map.id,
                    "extracted_preview_file": extracted_image_url,
                    "sha1": new_map_file.hash_sha1,
                },
            ),
            status=status.HTTP_201_CREATED,
        )

    def extract_preview(self, new_map_file: cnc_map.CncMapFile, map_parser: CncGen2MapParser | None) -> str | None:
        if not map_parser:
            return None

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

        return extracted_image_url

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
            "user": f"[{user.cncnet_id}] {user.username}" if user.is_authenticated else "unauthenticated_upload",
        }

    @staticmethod
    def _get_file_hashes(uploaded_file: File) -> MapHashes:
        map_hash_sha512 = file_utils.hash_file_sha512(uploaded_file)
        map_hash_md5 = file_utils.hash_file_md5(uploaded_file)
        map_hash_sha1 = file_utils.hash_file_sha1(uploaded_file)  # legacy ban list support

        return MapHashes(md5=map_hash_md5, sha1=map_hash_sha1, sha512=map_hash_sha512)

    def get_game_from_request(self, request: KirovyRequest) -> CncGame | None:
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
            code=UploadApiCodes.FILE_EXTENSION_NOT_SUPPORTED,
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
            cnc_map.CncMapFile.objects.filter(
                Q(hash_md5=hashes.md5) | Q(hash_sha512=hashes.sha512) | Q(hash_sha1=hashes.sha1)
            )
            .prefetch_related("cnc_map")
            .order_by("created")
            .all()
        )

        if not matched_hashes:
            return None

        is_banned = [x for x in matched_hashes if x.cnc_map.is_banned]

        if is_banned:
            log_attrs = {
                **self.user_log_attrs,
                "map_file_id": is_banned[0].id,
                "map_id": is_banned[0].cnc_map.id,
            }

            _LOGGER.info("attempted_uploading_banned_map_file", **log_attrs)

        raise KirovyValidationError(
            detail="This map file already exists",
            code=UploadApiCodes.DUPLICATE_MAP,
            additional={"existing_map_id": str(matched_hashes[0].cnc_map_id)},
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
                code=UploadApiCodes.EMPTY_UPLOAD,
            )
        if uploaded_size > settings.MAX_UPLOADED_FILE_SIZE_MAP:
            raise KirovyValidationError(
                detail="File too large",
                code=UploadApiCodes.FILE_TO_LARGE,
                additional={
                    "max_bytes": str(settings.MAX_UPLOADED_FILE_SIZE_MAP),
                    "your_bytes": str(uploaded_file),
                },
            )


class MapFileUploadView(_BaseMapFileUploadView):
    permission_classes = [permissions.CanUpload]
    upload_is_temporary = False

    def get_game_from_request(self, request: KirovyRequest) -> CncGame | None:
        game_id = request.data.get("game_id")
        return CncGame.objects.filter(id=game_id).first()


class CncnetClientMapUploadView(_BaseMapFileUploadView):
    """DO NOT USE THIS FOR NOW. Use"""

    permission_classes = [AllowAny]
    upload_is_temporary = True

    def get_game_from_request(self, request: KirovyRequest) -> CncGame | None:
        """Get the game ID for a CnCNet client upload.

        The client currently sends a slug in ``request.data["game"]``. The game table has a unique constraint
        on :attr:`kirovy.models.cnc_game.CncGame.slug` and the slugs were copied from
        `The legacy database <https://github.com/CnCNet/mapdb.cncnet.org/blob/75207fe70d4569d34372da1bf5c6691e8dc91ced/public/upload.php#L7C1-L14C3>`_
        We also added new games, like *Mental Omega*. Those slugs are defined in :file:`kirovy/migrations/0002_add_games.py`

        :param request:
        :return:
            The ID for the game corresponding to the slug from ``request.data["game"]``
        :raises KirovyValidationError:
            Raised if we can't find a game matching the slug.
        """
        game_slug = request.data.get("game")  # TODO: get game_slug after updating cncnet client.
        if not game_slug:
            raise KirovyValidationError(detail="Game name must be provided.", code=UploadApiCodes.MISSING_GAME_SLUG)

        try:
            game = CncGame.objects.get(slug__iexact=game_slug)
        except ObjectDoesNotExist:
            _LOGGER.warning(
                "client.map_upload: User attempted to upload for game slug that does not exist",
                attempted_slug=game_slug,
                **self.user_log_attrs,
            )
            raise KirovyValidationError(
                detail="Game with that name does not exist",
                code=UploadApiCodes.GAME_SLUG_DOES_NOT_EXIST,
                additional={"attempted_slug": game_slug},
            )

        return game


class CncNetBackwardsCompatibleUploadView(CncnetClientMapUploadView):
    """An endpoint to support backwards compatible uploads for clients that we don't control, or haven't been updated.

    Skips all post-processing and just drops the file in as-is.
    """

    permission_classes = [AllowAny]
    upload_is_temporary = True

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        uploaded_file: UploadedFile = request.data["file"]

        game = self.get_game_from_request(request)
        extension_id = self.get_extension_id_for_upload(uploaded_file)
        self.verify_file_size_is_allowed(uploaded_file)

        # Will raise validation errors if the upload is invalid
        legacy_map_service = legacy_upload.get_legacy_service_for_slug(game.slug.lower())(uploaded_file)

        map_hashes = self._get_file_hashes(ContentFile(legacy_map_service.file_contents_merged.read()))
        self.verify_file_does_not_exist(map_hashes)

        # Make the map that we will attach the map file to.
        new_map = cnc_map.CncMap(
            map_name=legacy_map_service.map_name,
            cnc_game=game,
            is_published=False,
            incomplete_upload=True,
            cnc_user=CncUser.objects.get_or_create_legacy_upload_user(),
            parent=None,
            is_mapdb1_compatible=True,
        )
        new_map.save()

        new_map_file_serializer = cnc_map_serializers.CncMapFileSerializer(
            data=dict(
                width=-1,
                height=-1,
                cnc_map_id=new_map.id,
                file=legacy_map_service.processed_zip_file(),
                file_extension_id=extension_id,
                cnc_game_id=game.id,
                hash_md5=map_hashes.md5,
                hash_sha512=map_hashes.sha512,
                hash_sha1=map_hashes.sha1,
            ),
            context={"request": self.request},
        )
        new_map_file_serializer.is_valid(raise_exception=True)
        new_map_file: cnc_map.CncMapFile = new_map_file_serializer.save()

        return KirovyResponse(
            ResultResponseData(
                message="File uploaded successfully",
                result={
                    "cnc_map": new_map.map_name,
                    "cnc_map_file": new_map_file.file.url,
                    "cnc_map_id": new_map.id,
                    "extracted_preview_file": None,
                    "download_url": f"/{game.slug}/{new_map_file.hash_sha1}.zip",
                },
            ),
            status=status.HTTP_200_OK,
        )
