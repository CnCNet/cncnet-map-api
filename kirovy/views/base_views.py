"""
Base views with common functionality for all API views in Kirovy
"""

from abc import ABCMeta

from django.core.files.uploadedfile import UploadedFile
from rest_framework import (
    exceptions as _e,
    generics as _g,
    permissions as _p,
    pagination as _pagination,
    status,
)
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import kirovy.objects.ui_objects
from kirovy import permissions, typing as t, logging
from kirovy.constants import api_codes
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.models import CncNetFileBaseModel
from kirovy.models.cnc_game import GameScopedUserOwnedModel, CncFileExtension
from kirovy.objects import ui_objects
from kirovy.permissions import CanUpload, CanEdit
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.serializers import KirovySerializer, CncNetUserOwnedModelSerializer


_LOGGER = logging.get_logger(__name__)


class KirovyDefaultPagination(_pagination.LimitOffsetPagination):
    """Default pagination values."""

    default_limit = 30
    max_limit = 200

    def get_paginated_response(self, results: t.List[t.DictStrAny]) -> KirovyResponse[ui_objects.ListResponseData]:
        data = kirovy.objects.ui_objects.ListResponseData(
            results=results,
            pagination_metadata=kirovy.objects.ui_objects.PaginationMetadata(
                offset=self.offset,
                limit=self.limit,
                remaining_count=self.count,
            ),
        )

        return KirovyResponse(data, status=status.HTTP_200_OK)

    # def get_paginated_response_schema(self, schema):
    #     raise NotImplementedError()


class KirovyListCreateView(_g.ListCreateAPIView):
    """Base view for listing and creating objects.

    It is up to subclasses to figure out how they want to filter large queries.
    """

    permission_classes = [permissions.CanUpload | permissions.ReadOnly]
    pagination_class: t.Optional[t.Type[KirovyDefaultPagination]] = KirovyDefaultPagination
    _paginator: t.Optional[KirovyDefaultPagination]
    request: KirovyRequest  # Added for type hinting. Populated by DRF ``.setup()``

    def create(self, request: KirovyRequest, *args, **kwargs) -> KirovyResponse[ui_objects.ResultResponseData]:
        data = request.data
        if isinstance(data, dict) and issubclass(self.get_serializer_class(), KirovySerializer):
            data["last_modified_by_id"] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        data = ui_objects.ResultResponseData(result=serializer.data)
        return KirovyResponse(data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs) -> KirovyResponse[ui_objects.ListResponseData]:
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        data = kirovy.objects.ui_objects.ListResponseData(results=serializer.data)
        return KirovyResponse(data, status=status.HTTP_200_OK)

    def get_paginated_response(self, data: t.List[t.DictStrAny]) -> KirovyResponse[ui_objects.ListResponseData]:
        """
        Return a paginated style `Response` object for the given output data.
        """
        return super().get_paginated_response(data)

    @property
    def paginator(self) -> t.Optional[KirovyDefaultPagination]:
        """Just here for type hinting."""
        return super().paginator


class KirovyRetrieveUpdateView(_g.RetrieveUpdateAPIView):
    """Base view for detail views and editing.

    We only allow partial updates because full updates always cause issues when two users are editing.

    e.g. Bob and Alice both have the page open. Alice updates an object, Bob doesn't refresh his page and updates
    the object. Bob's data doesn't have Alice's updates, so his stale data overwrites Alice's.
    """

    request: KirovyRequest  # Added for type hinting. Populated by DRF ``.setup()``
    permission_classes = [permissions.CanEdit | permissions.ReadOnly]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return KirovyResponse(
            kirovy.objects.ui_objects.ResultResponseData(
                result=serializer.data,
            ),
            status=status.HTTP_200_OK,
        )

    def put(self, request: KirovyRequest, *args, **kwargs) -> Response:
        raise _e.MethodNotAllowed(
            "PUT",
            "PUT is not allowed. Only use PATCH and only send fields that were modified.",
        )

    def delete(self, request: KirovyRequest, *args, **kwargs) -> Response:
        raise _e.MethodNotAllowed(
            "DELETE",
            "DELETE is not allowed on this endpoint. Please use the delete endpoint.",
        )


class KirovyRetrieveUpdateDestroyView(KirovyRetrieveUpdateView):
    """Prevents accidentally allowing deletes for CanEdit permissions until we allow user deletion."""

    pass


class KirovyDestroyView(_g.DestroyAPIView):
    """Base view for all delete endpoints in the app.

    For now, only admins can delete stuff.
    """

    request: KirovyRequest  # Added for type hinting. Populated by DRF ``.setup()``
    permission_classes = [permissions.CanDelete | _p.IsAdminUser]


class FileUploadBaseView(APIView, metaclass=ABCMeta):
    """A base class for uploading files that are **not** map files for a game."""

    parser_classes = [MultiPartParser]
    permission_classes: [CanUpload, CanEdit]
    request: KirovyRequest
    file_class: t.ClassVar[t.Type[CncNetFileBaseModel]]
    """attr: The class for the file."""
    file_parent_class: t.ClassVar[t.Type[GameScopedUserOwnedModel]]
    """attr: The class that the file will be linked to. e.g. the map this file belongs to."""

    file_parent_attr_name: t.ClassVar[str]
    """attr: The name of the foreign key to the parent object.

    This field must be present in ``request.data``.

    e.g. ``cnc_game_id``.
    """

    success_message: t.ClassVar[str]
    """attr: The message to send for a successful upload."""

    serializer_class: t.ClassVar[t.Type[CncNetUserOwnedModelSerializer]]

    def get_parent_object(self, request: KirovyRequest) -> GameScopedUserOwnedModel:

        parent_object_id = request.data.get(self.file_parent_attr_name)
        if not parent_object_id:
            raise KirovyValidationError(
                detail="Must specify foreign key to parent object",
                code=api_codes.FileUploadApiCodes.MISSING_FOREIGN_ID,
                additional={"expected_field": self.file_parent_attr_name},
            )

        parent_object: GameScopedUserOwnedModel = get_object_or_404(self.file_parent_class.objects, id=parent_object_id)
        self.check_object_permissions(request, parent_object)

        return parent_object

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse[ui_objects.ResultResponseData]:
        uploaded_file: UploadedFile = request.data["file"]
        parent_object = self.get_parent_object(request)
        self.extra_verification(request, uploaded_file, parent_object)

        extension_id = CncFileExtension.get_extension_id_for_upload(
            uploaded_file,
            self.file_class.ALLOWED_EXTENSION_TYPES,
            logger=_LOGGER,
            error_detail_upload_type="image",
            extra_log_attrs={"user_id": request.user.id, "username": request.user.username},
        )
        serializer = self.serializer_class(
            data={
                "cnc_game_id": parent_object.cnc_game_id,
                self.file_parent_attr_name: parent_object.id,
                "name": uploaded_file.name,
                "file": uploaded_file,
                "file_extension_id": extension_id,
                **self.extra_serializer_data(request, uploaded_file, parent_object),
            }
        )

        if not serializer.is_valid(raise_exception=False):
            raise KirovyValidationError("File failed validation", code=api_codes.FileUploadApiCodes.INVALID)

        serializer.save()
        saved: CncNetFileBaseModel = serializer.instance

        return KirovyResponse(
            ui_objects.ResultResponseData(
                message=self.success_message,
                result={
                    "file_id": saved.id,
                    "file_url": saved.file.url,
                    "parent_object_id": parent_object.id,
                },
            ),
            status=status.HTTP_201_CREATED,
        )

    def extra_serializer_data(
        self, request: KirovyRequest, uploaded_file: UploadedFile, parent_object: GameScopedUserOwnedModel
    ) -> t.Dict[str, t.Any]:
        raise NotImplementedError()

    def extra_verification(
        self, request: KirovyRequest, uploaded_file: UploadedFile, parent_object: GameScopedUserOwnedModel
    ) -> None:
        """Any extra verification that the file needs.

        :raises kirovy.exceptions.view_exceptions.KirovyValidationError:
            Raised for any issues.
        """
        raise NotImplementedError()
