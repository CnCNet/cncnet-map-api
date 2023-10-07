"""
Utils for the settings file, so don't import or use settings
in any function in this module.
"""
import os
from typing import Any, Optional, Callable, NoReturn

from kirovy import exceptions
from kirovy.typing import SettingsValidationCallback

MINIMUM_SECRET_KEY_LENGTH = 32


def get_env_var(
    key: str,
    default: Optional[Any] = None,
    validation_callback: Optional[SettingsValidationCallback] = None,
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
    :return Any:
        The env var value

    :raises exceptions.ConfigurationException:
        Raised for:
            - No env var value found and no default provided
            - Validation on the value failed.

    """

    value: Optional[Any] = os.environ.get(key)

    if value is None:
        value = default

    if value is None:
        raise exceptions.ConfigurationException(
            key, "Env var is required and cannot be None."
        )

    if validation_callback is not None:
        validation_callback(key, value)

    return value


def secret_key_validator(key: str, value: str) -> NoReturn:
    """Validate the secret key.

    :param str key:
        env var key.
    :param str value:
        The value found.
    :return NoReturn:

    :raises exceptions.ConfigurationException:
    """
    if len(value) < MINIMUM_SECRET_KEY_LENGTH:
        raise exceptions.ConfigurationException(
            key,
            f"EnvVar failed validation, length less than {MINIMUM_SECRET_KEY_LENGTH}",
        )
