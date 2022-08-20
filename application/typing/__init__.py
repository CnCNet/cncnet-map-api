"""
Any types specific to our application should live in this package.
"""

from typing import Callable, Any, NoReturn

# This is a type to pass to get_env_var to raise an exception if an env var is not valid.
# arg[0]: The key of the env var for the exception.
# arg[1]: The value we fetched from the env var
# No return, raise an error.
SettingsValidationCallback = Callable[[str, Any], NoReturn]
