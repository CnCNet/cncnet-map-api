"""
Any types specific to our application should live in this package.
"""

import uuid

# import typing for re-export. This avoids having two different typing imports.
from typing import *

# This is a type to pass to get_env_var to raise an exception if an env var is not valid.
# arg[0]: The key of the env var for the exception.
# arg[1]: The value we fetched from the env var
# No return, raise an error.
SettingsValidationCallback = Callable[[str, Any], None]


FileExtension = str

DictStrAny = Dict[str, Any]

TokenStr = str
""":attr: a string that we get from the ``BEARER`` http header."""


UuidStrOrUUID = Union[str, uuid.UUID]
""":attr: A uuid or str representation of a UUID for saving to the database."""

UiPermissionName = str
""":attr: A string passed to the UI to show/hide certain features. Does not control backend permissions, this is just
for UX."""

NO_VALUE = object()
""":attr: Used for cases where you want an optional parameter, but ``None`` is a valid value."""
