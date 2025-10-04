import datetime

from rest_framework import status

BASE_URL = "/admin/ban/"


def test_ban_has_permission(client_moderator, create_cnc_map, create_kirovy_user):
    user = create_kirovy_user(username="SethOfNOD")
    ban_reason = "Power shifts quickly in the Brotherhood"
    cnc_map = create_cnc_map(user_id=user.id)
    data = dict(
        object_type="map",
        is_banned=True,
        object_id=str(cnc_map.id),
        note=ban_reason,
    )

    response = client_moderator.post(BASE_URL, data=data)
    assert response.status_code == status.HTTP_200_OK
    cnc_map.refresh_from_db()

    assert cnc_map.is_banned
    assert cnc_map.ban_reason == ban_reason
    assert cnc_map.moderated_by == client_moderator.kirovy_user
    assert cnc_map.ban_date.date() == datetime.date.today()
    assert cnc_map.ban_count == 1

    ## Ban the user
    data = dict(
        object_type="user",
        is_banned=True,
        object_id=str(user.id),
        note=ban_reason,
    )

    response = client_moderator.post(BASE_URL, data=data)
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()

    assert user.is_banned
    assert user.ban_reason == ban_reason
    assert user.moderated_by == client_moderator.kirovy_user
    assert user.ban_date.date() == datetime.date.today()
    assert user.ban_count == 1


def test_ban_404(client_moderator):
    data = dict(
        object_type="map",
        is_banned=True,
        object_id="02a666d6-ea58-46bd-85e7-7ac1d8754cf5",  # if this test fails because of this istg
    )
    response = client_moderator.post(BASE_URL, data=data)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_ban_no_permission(client_user, create_kirovy_user, client_anonymous):
    user_to_try_to_ban = create_kirovy_user()
    data = dict(
        object_type="user",
        object_id=str(user_to_try_to_ban.id),
        is_banned=True,
    )
    response = client_user.post(BASE_URL, data=data)

    assert response.status_code == status.HTTP_403_FORBIDDEN

    ## attempt not logged in
    response = client_anonymous.post(BASE_URL, data=data)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_ban_cant_ban_legacy_maps(client_god, create_cnc_map, user, settings):
    """Sacred artifacts of the old internet can't be banned over the API."""
    sacred_artifact = create_cnc_map(user_id=user.id, is_legacy=True)
    data = dict(
        object_type="map",
        object_id=str(sacred_artifact.id),
        is_banned=True,
    )
    response = client_god.post(BASE_URL, data=data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "legacy-maps-cannot-be-banned"
