import requests
import json
import jwt
from django.conf import settings


def test_jwt():
    email_pass = {
        "email": settings.TESTING_API_USERNAME,
        "password": settings.TESTING_API_PASSWORD,
    }
    response = requests.post("https://ladder.cncnet.org/api/v1/auth/login", email_pass)

    assert response.status_code == 200
    data = json.loads(response.content)
    token = data.get("token")

    test = jwt.decode(
        token,
        options={"verify_signature": False},
        algorithms="HS256",
    )

    user_id = test.get("sub")

    header = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        "https://ladder.cncnet.org/api/v1/auth/refresh", headers=header
    )

    assert response.status_code == 200
