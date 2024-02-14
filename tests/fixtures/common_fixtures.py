import datetime
import json
from unittest import mock

import pytest
import requests
import ujson
from django.test import Client
from django.conf import (
    settings as _settings,
)  # Need to rename to not conflict with setting fixture.
from pytest_django.lazy_django import skip_if_no_django

from kirovy import objects, typing as t, constants
from kirovy.models import CncUser


@pytest.fixture
def raw_client(client, db) -> Client:
    """Used for testing endpoints without any kind of authentication mocking."""
    return client


@pytest.fixture
def create_auth_header():
    def _inner(bearer_token: str) -> dict:
        return {"Authorization": f"Bearer {bearer_token}"}

    return _inner


@pytest.fixture
def jwt_header(create_auth_header):
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
    return create_auth_header(token)


@pytest.fixture(autouse=True)
def tmp_media_root(tmp_path, settings):
    """Makes all file uploads go to tmp paths to not fill up developer drives."""
    tmp_media = tmp_path / settings.MEDIA_ROOT
    if not tmp_media.exists():
        tmp_media.mkdir(parents=True)
    settings.MEDIA_ROOT = tmp_media
    return settings.MEDIA_ROOT


class KirovyClient(Client):
    """A client wrapper with defaults I prefer.

    Our whole API will be JSON, so all write methods are wrapped to default to JSON.
    """

    cncnet_user_info: t.Optional[objects.CncnetUserInfo] = None
    kirovy_user: t.Optional[CncUser] = None

    JsonLike = t.Union[dict, str]
    __application_json: str = "application/json"

    def __convert_data(self, data: JsonLike, content_type: str) -> str:
        """Make the data compatible with json, if necessary."""
        if content_type == self.__application_json and isinstance(data, dict):
            data = ujson.dumps(data)
        return data

    def set_active_user(
        self,
        kirovy_user: t.Optional[CncUser] = None,
        cncnet_user_info: t.Optional[objects.CncnetUserInfo] = None,
    ) -> None:
        """Set the active user for requests.

        You must set the CnCNet info, or the kirovy user.

        Setting just ``cncnet_user_info`` will mimic a user
        that exists in CnCNet, but doesn't yet exist in Kirovy.

        :param kirovy_user:
            The user in kirovy's database.
        :param cncnet_user_info:
            The mock CnCNet user info.
        """
        assert kirovy_user or cncnet_user_info

        if cncnet_user_info and not kirovy_user:
            # Don't let programmers attempt to emulate creating a user, via JWT, when the user already exists.
            assert not CncUser.objects.find_by_cncnet_id(cncnet_user_info.id)
        self.kirovy_user = kirovy_user
        self.cncnet_user_info = cncnet_user_info

    def request(self, **request):
        """Wraps request to mock the authenticate method to return our "active" user."""
        with mock.patch(
            "kirovy.authentication.CncNetAuthentication.authenticate"
        ) as mocked:
            if not self.kirovy_user:
                mocked.return_value = None
            else:
                mocked.return_value = self.kirovy_user, self.cncnet_user_info
            return super().request(**request)

    def post(
        self,
        path,
        data=None,
        content_type=__application_json,
        follow=False,
        secure=False,
        **extra,
    ):
        """Wraps post to make it default to JSON."""

        data = self.__convert_data(data, content_type)
        return super().post(
            path,
            data=data,
            content_type=content_type,
            follow=follow,
            secure=secure,
            **extra,
        )

    def patch(
        self,
        path,
        data: JsonLike = "",
        content_type=__application_json,
        follow=False,
        secure=False,
        **extra,
    ):
        """Wraps patch to make it default to JSON."""

        data = self.__convert_data(data, content_type)
        return super().patch(
            path,
            data=data,
            content_type=content_type,
            follow=follow,
            secure=secure,
            **extra,
        )

    def put(
        self,
        path,
        data: JsonLike = "",
        content_type=__application_json,
        follow=False,
        secure=False,
        **extra,
    ):
        """Wraps put to make it default to JSON."""

        data = self.__convert_data(data, content_type)
        return super().put(
            path,
            data=data,
            content_type=content_type,
            follow=follow,
            secure=secure,
            **extra,
        )


@pytest.fixture
def create_client(db):
    """Return a factory to create a kirovy test http client.

    The db fixture is included because you'll probably want DB access
    any time you're hitting the API.
    """

    def _inner(
        active_user: t.Optional[CncUser] = None,
        cnc_user_info: t.Optional[objects.CncnetUserInfo] = None,
    ) -> KirovyClient:
        skip_if_no_django()
        client = KirovyClient()
        if active_user is not None:
            client.set_active_user(active_user, cnc_user_info)
        return client

    return _inner


@pytest.fixture
def kirovy_client(create_client) -> KirovyClient:
    """An unauthenticated Kirovy test client instance."""
    return create_client()


@pytest.fixture
def create_kirovy_user(db):
    """Return a user creation factory."""

    def _inner(
        cncnet_id: int = 686,
        username: str = "EbullientPrism",
        verified_map_uploader: bool = True,
        verified_email: bool = True,
        group: constants.CncnetUserGroup.RoleType = constants.CncnetUserGroup.USER,
        is_banned: bool = False,
        ban_reason: t.Optional[str] = None,
        ban_date: t.Optional[datetime.datetime] = None,
        ban_expires: t.Optional[datetime.datetime] = None,
        ban_count: int = 0,
    ) -> CncUser:
        """Create a kirovy user according to the kwargs.

        See the model for param descriptions.
        :class:`~kirovy.models.cnc_user.CncUser`
        """
        user = CncUser(
            cncnet_id=cncnet_id,
            username=username,
            verified_map_uploader=verified_map_uploader,
            verified_email=verified_email,
            group=group,
            is_banned=is_banned,
            ban_reason=ban_reason,
            ban_date=ban_date,
            ban_expires=ban_expires,
            ban_count=ban_count,
        )
        user.save()
        user.refresh_from_db()
        return user

    return _inner


@pytest.fixture
def user(create_kirovy_user):
    """Convenience method to create a user."""
    return create_kirovy_user()


@pytest.fixture
def moderator(create_kirovy_user) -> CncUser:
    """Convenience method to create a moderator."""
    return create_kirovy_user(
        cncnet_id=117649, username="DespondentPyre", group=constants.CncnetUserGroup.MOD
    )


@pytest.fixture
def admin(create_kirovy_user) -> CncUser:
    """Convenience method to create an admin."""
    return create_kirovy_user(
        cncnet_id=49, username="MendicantBias", group=constants.CncnetUserGroup.ADMIN
    )


@pytest.fixture
def god(create_kirovy_user) -> CncUser:
    """Convenience method to create a god."""
    return create_kirovy_user(
        cncnet_id=1, username="ThePrimordial", group=constants.CncnetUserGroup.GOD
    )


@pytest.fixture
def client_user(user, create_client) -> KirovyClient:
    """Returns a client with an active admin user."""
    return create_client(user)


@pytest.fixture
def client_moderator(moderator, create_client) -> KirovyClient:
    """Returns a client with an active moderator user."""
    return create_client(moderator)


@pytest.fixture
def client_admin(admin, create_client) -> KirovyClient:
    """Returns a client with an active admin user."""
    return create_client(admin)


@pytest.fixture
def client_god(god, create_client) -> KirovyClient:
    """Returns a client with an active god user."""
    return create_client(god)
