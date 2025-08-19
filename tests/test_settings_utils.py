import os

import pytest

from kirovy import exceptions, typing as t
from kirovy.utils import settings_utils


@pytest.mark.parametrize(
    "run_environment,expect_error",
    [
        ("dev", False),
        ("test", False),
        ("prod", True),
        ("PRODUCTION", True),
        ("ci", False),
    ],
)
def test_cannot_enable_with_prod(mocker, run_environment: str, expect_error: bool):
    mocker.patch.dict(os.environ, {"RUN_ENVIRONMENT": run_environment})

    if expect_error:
        with pytest.raises(exceptions.ConfigurationException):
            settings_utils.get_env_var("meh", True, settings_utils.not_allowed_on_prod)
    else:
        settings_utils.get_env_var("meh", True, settings_utils.not_allowed_on_prod)


@pytest.mark.parametrize(
    "run_environment,expect_error",
    [
        ("dev", False),
        ("test", False),
        ("prod", False),
        ("PRODUCTION", False),
        ("ci", False),
    ],
)
def test_cannot_enable_with_prod__is_false(mocker, run_environment: str, expect_error: bool):
    """Test that a setting being false will never trigger the not_allowed_on_prod check."""
    mocker.patch.dict(os.environ, {"RUN_ENVIRONMENT": run_environment})
    settings_utils.get_env_var("meh", False, settings_utils.not_allowed_on_prod)


@pytest.mark.parametrize(
    "run_environment,expect_error",
    [
        ("dev", False),
        ("ci", False),
        ("prod", False),
        ("PRODUCTION", True),
        ("cncnet", True),
    ],
)
def test_run_environment_valid(run_environment: str, expect_error: bool):
    if expect_error:
        with pytest.raises(exceptions.ConfigurationException) as e:
            settings_utils.get_env_var("meh", run_environment, settings_utils.run_environment_valid)
        assert e
    else:
        settings_utils.get_env_var("meh", run_environment, settings_utils.run_environment_valid)


@pytest.mark.parametrize(
    "value,expected,value_type",
    [
        ("1", 1, int),
        ("1.1", 1.1, float),
        ("1", "1", str),
        ("1", True, bool),
        ("true", True, bool),
        ("0", False, bool),
        ("false", False, bool),
    ],
)
def test_get_env_var_value(mocker, value: str, expected: t.Any, value_type: t.Type[t.Any]):
    """Test the strings can be properly cast using the environment loader.

    Necessary because ``environ.get`` always returns ``str | None``.
    """
    mocker.patch.dict(os.environ, {"test_get_env_var_value": value})
    assert settings_utils.get_env_var("test_get_env_var_value", value_type=value_type) == expected
