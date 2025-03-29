import os

import pytest

from kirovy import exceptions
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
