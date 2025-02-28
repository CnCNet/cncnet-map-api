"""
All exceptions for our app belong in this package.
"""

from django.core.exceptions import *  # Import django exceptions for use elsewhere.
from typing import Optional
from django.utils.translation import gettext_lazy as _


from rest_framework.exceptions import UnsupportedMediaType

from .auth_exceptions import *


class ConfigurationException(Exception):
    """Exception to raise when an env var isn't correct.

    Raise from :func:`~kirovy.utils.settings_utils.get_env_var` or your callback.
    """

    key: str
    message: Optional[str]

    def __init__(
        self,
        key: str,
        message: Optional[str] = None,
    ):
        super().__init__(message)

        self.key = key
        self.message = message

    def __str__(self) -> str:
        message = super().__str__()
        message = f"{message}: key={self.key}"

        return message


class InvalidFileExtension(ValidationError):
    """Raised when trying to create an invalid file extension in the database."""

    pass


class InvalidMimeType(ValidationError):
    """Raised when we e.g. expect text, but get a binary file."""

    pass


class InvalidMapFile(ValidationError):
    """Raised when a map can't be parsed or if it's missing a header."""

    pass


class MapPreviewCorrupted(ValidationError):
    """Raised when a map's ``Preview.Size`` doesn't match the ``PreviewPack`` data size."""

    pass


class GameNotSupportedError(UnsupportedMediaType):
    """Raised when a game is not yet supported."""

    default_detail = _('Game is not yet supported "{media_type}"')
    default_code = "unsupported_game"

    def __init__(
        self,
        game_name_or_slug: str,
        detail: Optional[str] = None,
        code: Optional[int] = None,
    ):
        super().__init__(game_name_or_slug, detail, code)


class BanException(Exception):
    """Raised when there is an issue during the ban process.

    ``str(e)`` will be returned to the UI.
    """

    pass
