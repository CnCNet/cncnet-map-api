import datetime

import pytest
import requests
import json
import jwt
from django.conf import settings as test_settings
from rest_framework import status

from kirovy.settings import settings_constants

needs_cncnet_auth = pytest.mark.skipif(
    test_settings.RUN_ENVIRONMENT == settings_constants.RunEnvironment.CI,
    reason="Need to provide CnCNet credentials to call CnCNet endpoints in tests. "
    "Set TESTING_API_USERNAME/PASSWORD in .env. Do NOT commit your env.",
)


@needs_cncnet_auth
def test_jwt():
    """This test exists purely so that I can look at things coming from cncnet.

    If it ever becomes an issue for the test pipeline then just mark it as ``pytest.mark.skip`` or delete it.
    """
    email_pass = {
        "email": test_settings.TESTING_API_USERNAME,
        "password": test_settings.TESTING_API_PASSWORD,
    }
    response = requests.post("https://ladder.cncnet.org/api/v1/auth/login", email_pass)

    assert response.status_code == 200
    login_data = json.loads(response.content)
    token = login_data.get("token")

    test = jwt.decode(
        token,
        options={"verify_signature": False},
        algorithms="HS256",
    )
    expires = datetime.datetime.fromtimestamp(test["exp"])

    user_id = test.get("sub")

    header = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://ladder.cncnet.org/api/v1/user/info", headers=header)
    info_data = json.loads(response.content)

    assert response.status_code == 200
    assert str(info_data["id"]) == user_id
    assert expires > datetime.datetime.now()


@needs_cncnet_auth
def test_jwt_endpoint(raw_client, jwt_header, settings):
    """Test that the JWT test endpoint works when debug is enabled."""
    settings.DEBUG = True
    response = raw_client.get("/test/jwt", headers=jwt_header)
    assert response.status_code == status.HTTP_200_OK
    assert response.data == test_settings.TESTING_API_USERNAME


@needs_cncnet_auth
def test_jwt_endpoint__debug_disabled(raw_client, jwt_header):
    response = raw_client.get("/test/jwt", headers=jwt_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN
