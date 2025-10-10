from rest_framework.views import exception_handler

from kirovy.exceptions.view_exceptions import KirovyAPIException
from kirovy.objects import ui_objects
from kirovy.response import KirovyResponse


def kirovy_exception_handler(exception: Exception, context) -> KirovyResponse[ui_objects.ErrorResponseData] | None:
    """Exception handler to deal with our custom exception types.

    This gets called via the setting ``REST_FRAMEWORK['EXCEPTION_HANDLER']``.
    :attr:`kirovy.settings._base.REST_FRAMEWORK`

    .. note::

        `The DRF docs <https://www.django-rest-framework.org/api-guide/exceptions/#custom-exception-handling>`_

    :param exception:
        The raised exception.
    :param context:
    :return:
        Returns the ``KirovyResponse`` if the exception is one we defined.
        Otherwise, it calls the base DRF exception handler :func:`rest_framework.views.exception_handler`.
    """
    if isinstance(exception, KirovyAPIException):
        return KirovyResponse(exception.as_error_response_data(), status=exception.status_code)

    return exception_handler(exception, context)
