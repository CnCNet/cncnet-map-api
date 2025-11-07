import io
import pathlib

from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.db.models import QuerySet

from kirovy import permissions, typing as t
from kirovy.constants import api_codes
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.models import CncMap
from kirovy.models.cnc_game import GameScopedUserOwnedModel
from kirovy.models.cnc_map import CncMapImageFile
from kirovy.request import KirovyRequest
from kirovy.serializers import cnc_map_serializers
from kirovy.views import base_views
from kirovy.views.cnc_map_views import _LOGGER


class MapImageFileUploadView(base_views.FileUploadBaseView):
    """Endpoint for uploading map images.

    The map ID that this image belongs to must be in the POST data with the attr ``cnc_map_id``.
    """

    permission_classes = [permissions.CanEdit]
    serializer_class = cnc_map_serializers.CncMapImageFileSerializer
    file_class = CncMapImageFile
    file_parent_class = CncMap
    file_parent_attr_name = "cnc_map_id"
    success_message = "Map image uploaded successfully."

    def extra_serializer_data(
        self, request: KirovyRequest, uploaded_file: UploadedFile, parent_object: CncMap
    ) -> t.Dict[str, t.Any]:
        latest_image: CncMapImageFile | None = (
            CncMapImageFile.objects.filter(cnc_map_id=parent_object.id)
            .order_by("-image_order")
            .only("image_order")
            .first()
        )
        with Image.open(uploaded_file) as image:
            height = image.height
            width = image.width
        return {
            "height": height,
            "width": width,
            "is_extracted": False,
            "image_order": latest_image.image_order if latest_image else 0,
        }

    def extra_verification(self, request: KirovyRequest, uploaded_file: UploadedFile, parent_object: CncMap) -> None:
        if parent_object.is_legacy or parent_object.is_temporary:
            raise KirovyValidationError(
                "Map type does not support custom preview images", code=api_codes.FileUploadApiCodes.UNSUPPORTED
            )
        try:
            with Image.open(uploaded_file) as maybe_image:
                maybe_image.verify()
        except (DecompressionBombError, UnidentifiedImageError) as e:
            _LOGGER.warning(
                "user-attempted-bad-image-upload",
                **{"user_id": str(request.user.id), "username": request.user.username, "e": str(e)},
            )
            raise KirovyValidationError("Image is invalid", code=api_codes.FileUploadApiCodes.INVALID)

    def modify_uploaded_file(
        self, request: KirovyRequest, uploaded_file: UploadedFile, parent_object: GameScopedUserOwnedModel
    ) -> InMemoryUploadedFile | UploadedFile:
        """Compress the image to jpeg."""
        filename = pathlib.Path(uploaded_file.name).stem
        with Image.open(uploaded_file) as image:
            image_io = io.BytesIO()
            # This should also remove metadata.
            image.convert("RGB").save(image_io, format="JPEG", quality=95)

        return InMemoryUploadedFile(image_io, None, f"{filename}.jpg", "image/jpeg", image_io.tell(), None)


class MapImageFileRetrieveUpdateDestroy(base_views.KirovyRetrieveUpdateDestroyView):
    """Endpoint to edit the editable fields for a map image."""

    serializer_class = cnc_map_serializers.CncMapImageFileSerializer
    allow_simple_destroy = True

    def get_queryset(self) -> QuerySet[CncMapImageFile]:
        base = CncMapImageFile.objects.filter(cnc_map__is_banned=False)
        if self.request.user.is_authenticated:
            return base | CncMapImageFile.objects.filter(cnc_user_id=self.request.user.id)

        return base
