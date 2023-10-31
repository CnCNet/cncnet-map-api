import json

import requests
from django.http import HttpRequest
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from kirovy import exceptions

from kirovy import typing as t, constants, objects
from kirovy.models import CncUser


class CncNetAuthentication(BaseAuthentication):
    def authenticate(
        self, request: t.Optional[HttpRequest]
    ) -> t.Tuple[t.Optional[CncUser], t.Optional[objects.CncnetUserInfo]]:
        auth_header: t.Optional[str] = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            return None, None

        token: t.List[str] = auth_header.strip().split(" ")
        if len(token) != 2 or token[0].lower() != "bearer":
            raise exceptions.MalformedTokenError()

        cncnet_response = requests.get(
            constants.cncnet_user_url, headers=request.headers
        )

        if cncnet_response.status_code != status.HTTP_200_OK:
            raise exceptions.CncNetAuthFailed(
                cncnet_response.text, cncnet_response.status_code
            )

        data = json.loads(cncnet_response.content)
        user_dto = objects.CncnetUserInfo(**data)

        if not user_dto.id:
            raise AuthenticationFailed(
                "could-not-parse-user-info-from-cncnet", status.HTTP_401_UNAUTHORIZED
            )

        map_user = CncUser.create_or_update_from_cncnet(user_dto)

        return map_user, user_dto
