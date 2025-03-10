from rest_framework import status
from rest_framework.exceptions import APIException as _DRFAPIException
from django.utils.translation import gettext_lazy as _

from kirovy import typing as _t
from kirovy.objects import ui_objects


class KirovyValidationError(_DRFAPIException):
    """A custom exception that easily converts to the standard ``ErrorResponseData``

    See: :class:`kirovy.objects.ui_objects.ErrorResponseData`

    This exception is meant to be used within serializers or views.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Invalid input.")
    default_code = "invalid"
    additional: _t.DictStrAny | None = None
    code: str | None
    detail: str | None

    def __init__(self, detail: str | None = None, code: str | None = None, additional: _t.DictStrAny | None = None):
        super().__init__(detail=detail, code=code)
        self.additional = additional

    def as_error_response_data(self) -> ui_objects.ErrorResponseData:
        return ui_objects.ErrorResponseData(message=self.detail, code=self.code, additional=self.additional)
