"""
All exceptions for our app belong in this package.
"""
from django.core.exceptions import *  # Import django exceptions for use elsewhere.
from typing import Optional


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
