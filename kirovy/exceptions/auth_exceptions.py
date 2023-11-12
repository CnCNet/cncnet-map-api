from rest_framework import exceptions as drf_exceptions, status

__all__ = ["MalformedTokenError", "CncNetAuthFailed"]


class MalformedTokenError(drf_exceptions.AuthenticationFailed):
    """Raised when headers don't have ``Authorization: Bearer {TOKEN}``."""

    default_detail = "malformed-token"
    default_code = status.HTTP_400_BAD_REQUEST


class CncNetAuthFailed(drf_exceptions.AuthenticationFailed):
    """Raised when a token was successfully parsed, but an error occured calling CncNet.

    Pass in the detail and status from CncNet.
    """

    default_detail = ""
    default_code = status.HTTP_401_UNAUTHORIZED
