import dataclasses
import json

import jwt
import requests
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from rest_framework import status
from rest_framework.response import Response

from kirovy import typing as t, constants, objects
from kirovy.models.cnc_user import CncUser


class JwtMiddleware:
    def __init__(self, get_response: t.Callable[[WSGIRequest], Response]):
        self.get_response = get_response

    def __call__(self, request: WSGIRequest) -> Response:
        cncnet_response = requests.get(
            constants.cncnet_user_url, headers=request.headers
        )

        if cncnet_response.status_code != status.HTTP_200_OK:
            return Response(status=cncnet_response.status_code)

        data = json.loads(cncnet_response.content)
        user_dto = objects.CncnetUserInfo(**data)

        if not user_dto.id:
            return Response(
                data={"reason": "user-not-found"}, status=status.HTTP_401_UNAUTHORIZED
            )

        map_user = CncUser.create_or_update_from_cnc_net(user_dto)

        response = self.get_response(request)

        return response
