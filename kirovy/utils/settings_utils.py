"""
Utils for the settings file, so don't import or use settings
in any function in this module.
"""

import os
from collections.abc import Callable

from distutils.util import strtobool
from typing import Any, Type

from kirovy import exceptions
from kirovy.typing import SettingsValidationCallback
from kirovy.settings import settings_constants

MINIMUM_SECRET_KEY_LENGTH = 32
_NOT_SET = object()


def _unvalidated_env_var(_: str, __: Any) -> None:
    return


def get_env_var(
    key: str,
    default: Any | None = _NOT_SET,
    validation_callback: SettingsValidationCallback = _unvalidated_env_var,
    *,
    value_type: Type[Callable[[object], Any]] = str,
) -> Any:
    """Get an env var and validate it.

    If you do not provide a default then the value is considered "required"
    and the programmer must set it in their .env file.

    Do not provide defaults for e.g. passwords.

    :param str key:
        The env var key to search for.
    :param Optional[Any] default:
        The default value. Use to make an env var not raise an error if
        no env var is found. Never use for secrets.
        If you use with ``validation_callback`` then make sure your default value will
        pass your validation check.
    :param Optional[SettingsValidationCallback] validation_callback:
        A function to call on a value to make sure it's valid.
        Raises an exception if invalid.
    :param value_type:
        Convert the string from ``os.environ`` to this type. The type must be callable.
        No validation is performed on the environment string before attempting to cast,
        so you're responsible for handling cast errors.

        .. note::

            If you provide ``bool`` then we will use ``distutils.util.strtobool``.
    :return Any:
        The env var value

    :raises exceptions.ConfigurationException:
        Raised for:
            - No env var value found and no default provided
            - Validation on the value failed.

    """

    value: str | None = os.environ.get(key)

    if value is None and default is _NOT_SET:
        raise exceptions.ConfigurationException(key, "Env var is required and cannot be None.")

    if value_type == bool:
        value_type = strtobool

    value = value_type(value) if value is not None else default

    validation_callback(key, value)

    return value


def secret_key_validator(key: str, value: str) -> None:
    """Validate the secret key.

    :param str key:
        env var key.
    :param str value:
        The value found.
    :return:

    :raises exceptions.ConfigurationException:
    """
    if len(value) < MINIMUM_SECRET_KEY_LENGTH:
        raise exceptions.ConfigurationException(
            key,
            f"EnvVar failed validation, length less than {MINIMUM_SECRET_KEY_LENGTH}",
        )


def not_allowed_on_prod(key: str, value: bool) -> None:
    if value and settings_constants.RunEnvironment.PRODUCTION in get_env_var("RUN_ENVIRONMENT", "").lower():
        raise exceptions.ConfigurationException(key, "Cannot be enabled on prod.")


def run_environment_valid(key: str, value: str) -> None:
    if value not in settings_constants.RunEnvironment:
        raise exceptions.ConfigurationException(
            key,
            f"Not a valid run environment: options={[x.value for x in settings_constants.RunEnvironment]}, {value=}",
        )
