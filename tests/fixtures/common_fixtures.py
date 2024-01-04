import json

import pytest
import requests
from django.test import Client
from django.conf import (
    settings as _settings,
)  # Need to rename to not conflict with setting fixture.


@pytest.fixture
def cnc_client(client, db) -> Client:
    return client


@pytest.fixture(scope="session")
def jwt_header():
    """Generates headers for calls to JWT protected endpoints.

    You need an account on CncNet and the environment variables for the credentials set.
    """
    email_pass = {
        "email": _settings.TESTING_API_USERNAME,
        "password": _settings.TESTING_API_PASSWORD,
    }
    response = requests.post("https://ladder.cncnet.org/api/v1/auth/login", email_pass)

    assert response.status_code == 200
    data = json.loads(response.content)
    token = data.get("token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def tmp_media_root(tmp_path, settings):
    """Makes all file uploads go to tmp paths to not fill up developer drives."""
    tmp_media = tmp_path / settings.MEDIA_ROOT
    if not tmp_media.exists():
        tmp_media.mkdir(parents=True)
    settings.MEDIA_ROOT = tmp_media
    return settings.MEDIA_ROOT
