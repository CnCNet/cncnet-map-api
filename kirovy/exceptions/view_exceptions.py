from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.exceptions import APIException as _DRFAPIException
from django.utils.translation import gettext_lazy as _

from kirovy import typing as _t
from kirovy.objects import ui_objects


class KirovyAPIException(_DRFAPIException):
    status_code: _t.ClassVar[int] = status.HTTP_500_INTERNAL_SERVER_ERROR
    additional: _t.DictStrAny | None = None
    code: str | None
    """attr: Some kind of string that the UI will recognize. e.g. ``file-too-large``.

    Maps to the UI object attr :attr:`kirovy.objects.ui_objects.ErrorResponseData.code`.

    .. warning::

        This is **not** the HTTP code. The HTTP code will always be ``400`` for validation errors.
    """
    detail: str | None
    """attr: Extra detail in plain language. Think of this as a message for the user.

    Maps to the UI object attr :attr:`kirovy.objects.ui_objects.ErrorResponseData.message`.
    """

    def __init__(self, detail: str | None = None, code: str | None = None, additional: _t.DictStrAny | None = None):
        super().__init__(detail=detail, code=code)
        self.code = str(code) if code else self.default_code
        self.detail = str(detail) if detail else self.default_detail
        self.additional = additional

    def as_error_response_data(self) -> ui_objects.ErrorResponseData:
        return ui_objects.ErrorResponseData(message=self.detail, code=self.code, additional=self.additional)


class KirovyValidationError(KirovyAPIException):
    """A custom exception that easily converts to the standard ``ErrorResponseData``

    See: :class:`kirovy.objects.ui_objects.ErrorResponseData`

    This exception is meant to be used within serializers or views.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Invalid input.")
    default_code = "invalid"


class KirovyMethodNotAllowed(KirovyAPIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    default_detail = _('Method "{method}" not allowed.')
    default_code = "method_not_allowed"

    def __init__(
        self, method, detail: str | None = None, code: str | None = None, additional: _t.DictStrAny | None = None
    ):
        if detail is None:
            detail = force_str(self.default_detail).format(method=method)
        super().__init__(detail, code, additional)
