import json

import requests
from django.http import HttpRequest
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from kirovy import exceptions

from kirovy import typing as t, constants, objects
from kirovy.models import CncUser


class CncNetAuthenticator:
    """The class for sending requests to the cncnet Ladder API.

    This exists to house logic related to authenticating with CnCNet,
    and to easily monkey-patch CnCNet auth in tests.
    """

    @classmethod
    def authenticate(
        cls, request: HttpRequest
    ) -> t.Tuple[CncUser, t.Optional[objects.CncnetUserInfo]]:
        """Authenticate a request's JWT with CnCNet.

        Monkeypatch this function in tests to return whichever value you need
        for testing endpoint permissions.

        :param request:
            The request to Kirovy. We will send its header to CnCNet.
        :return:
            [0] - The Kirovy user object that represents the CncNet user
            [1] - The raw user data returned from CnCNet, if you need it.

        :raises exceptions.CncNetAuthFailed:
            Raised if we don't receive a ``200`` from CnCNet.
        :raises AuthenticationFailed:
            Raised if we successfully authenticate with CnCNet, but can't parse the user info.
        """
        user_dto = cls.request_user_info(request)
        kirovy_user = CncUser.create_or_update_from_cncnet(user_dto)

        return kirovy_user, user_dto

    @staticmethod
    def request_user_info(request: HttpRequest) -> objects.CncnetUserInfo:
        """Send a request to CnCNet to get user info.

        Monkeypatch this if you want to test a request creating a new user from a token.

        :param request:
            The raw HttpRequest.
        :return:
            The CnCNet user info, if the request succeeded.

        :raises exceptions.CncNetAuthFailed:
            Raised if we don't receive a ``200`` from CnCNet.
        :raises AuthenticationFailed:
            Raised if we successfully authenticate with CnCNet, but can't parse the user info.
        """
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

        return user_dto


class CncNetAuthentication(BaseAuthentication):
    def authenticate(
        self, request: t.Optional[HttpRequest]
    ) -> t.Optional[t.Tuple[CncUser, objects.CncnetUserInfo]]:
        """Authenticate a request with CnCNet.

        Extracts the JWT from ``request.headers`` then forwards that to CnCNet.
        If the JWT authenticates, then get, or create, the Kirovy user object for the CnCNet user.

        :param request:
            The raw request.
        :return:
            [0] - The Kirovy user object that represents the CncNet user
            [1] - The raw user data returned from CnCNet, if you need it.
        """
        auth_header: t.Optional[str] = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            return None

        token: t.List[str] = auth_header.strip().split(" ")
        if len(token) != 2 or token[0].lower() != "bearer":
            raise exceptions.MalformedTokenError()

        return CncNetAuthenticator.authenticate(request)
