import pathlib

from django.core.files.uploadedfile import UploadedFile
from structlog.stdlib import BoundLogger

from kirovy import typing as t
from kirovy.constants.api_codes import UploadApiCodes
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.models import CncFileExtension


class FileExtensionService:

    @staticmethod
    def get_extension_id_for_upload(
        uploaded_file: UploadedFile,
        allowed_types: t.Set[str],
        *,
        logger: BoundLogger,
        error_detail_upload_type: str,
        extra_log_attrs: t.Dict[str, t.Any] | None = None,
    ) -> str:
        uploaded_extension = pathlib.Path(uploaded_file.name).suffix.lstrip(".").lower()
        # iexact is case insensitive
        kirovy_extension = CncFileExtension.objects.filter(
            extension__iexact=uploaded_extension,
            extension_type__in=allowed_types,
        ).first()

        if kirovy_extension:
            return str(kirovy_extension.id)

        logger.warning(
            "User attempted uploading unknown filetype",
            uploaded_extension=uploaded_extension,
            **(extra_log_attrs or {}),  # todo: the userattrs should be a context tag for structlog.
        )
        raise KirovyValidationError(
            detail=f"'{uploaded_extension}' is not a valid {error_detail_upload_type.strip()} file extension.",
            code=UploadApiCodes.FILE_EXTENSION_NOT_SUPPORTED,
        )
