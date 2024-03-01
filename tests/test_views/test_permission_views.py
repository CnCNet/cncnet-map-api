from rest_framework import status

from kirovy.permissions import UiPermissions

BASE_URL = "/ui-permissions/"


def test_permissions_banned_not_signed_in_not_verified(
    client_anonymous, client_banned, client_not_verified
):
    for client in [client_banned, client_anonymous, client_not_verified]:
        response = client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        for permission_key, has_permission in response.data["result"].items():
            assert not has_permission


def test_permissions_normal_user(client_user):
    response = client_user.get(BASE_URL)

    assert response.status_code == status.HTTP_200_OK

    assert response.data["result"] == {
        UiPermissions.SHOW_UPLOAD_BUTTON: True,
        UiPermissions.SHOW_STAFF_CONTROLS: False,
        UiPermissions.SHOW_ADMIN_CONTROLS: False,
    }


def test_permissions_staff_moderator(client_moderator):
    response = client_moderator.get(BASE_URL)

    assert response.status_code == status.HTTP_200_OK

    assert response.data["result"] == {
        UiPermissions.SHOW_UPLOAD_BUTTON: True,
        UiPermissions.SHOW_STAFF_CONTROLS: True,
        UiPermissions.SHOW_ADMIN_CONTROLS: False,
    }


def test_permissions_admin_god(client_admin, client_god):
    for client in [client_admin, client_god]:
        response = client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK

        assert response.data["result"] == {
            UiPermissions.SHOW_UPLOAD_BUTTON: True,
            UiPermissions.SHOW_STAFF_CONTROLS: True,
            UiPermissions.SHOW_ADMIN_CONTROLS: True,
        }
