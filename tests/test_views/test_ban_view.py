import datetime

from django.utils.html import escape
from rest_framework import status

from kirovy import constants

BASE_URL = "/admin/ban/"


def test_ban_user_and_map(client_moderator, create_cnc_map, create_kirovy_user):
    user = create_kirovy_user(username="SethOfNOD")
    ban_reason = "Power shifts quickly in the Brotherhood"
    cnc_map = create_cnc_map(user_id=user.id)
    data = dict(
        object_type="map",
        is_banned=True,
        object_id=str(cnc_map.id),
        note=ban_reason,
    )

    today = datetime.date.today()
    response = client_moderator.post(BASE_URL, data=data)
    assert response.status_code == status.HTTP_200_OK
    cnc_map.refresh_from_db()

    assert cnc_map.is_banned
    assert cnc_map.ban_reason == ban_reason
    assert cnc_map.moderated_by == client_moderator.kirovy_user
    assert cnc_map.ban_date.date() == datetime.date.today()
    assert cnc_map.ban_count == 1
    assert cnc_map.moderator_notes == (
        f"- Banned [{today.isoformat()}]: {ban_reason} -- by: '{client_moderator.kirovy_user.username}'\n"
    )

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
    assert user.ban_date.date() == today
    assert user.ban_count == 1
    assert user.moderator_notes == (
        f"- Banned [{today.isoformat()}]: {ban_reason} -- by: '{client_moderator.kirovy_user.username}'\n"
    )


def test_ban_unban_and_moderator_notes(create_client, create_kirovy_user):
    """Test banning and unbanning. Test Moderator Notes through multiple actions."""
    # Two different mods performing actions
    mod_gdi = create_kirovy_user(username="GDI", group=constants.CncnetUserGroup.MOD)
    mod_kane = create_kirovy_user(username="Kane", group=constants.CncnetUserGroup.MOD)
    mod_client_gdi = create_client(mod_gdi)
    mod_client_kane = create_client(mod_kane)
    cabal = create_kirovy_user(username="CABAL")

    # Multiple bans, the ban reasons should be kept in the log.
    ban_reason_1 = "Being rude to humans"
    ban_reason_2 = "Making the core defender"
    unban_reason = "Needed for Kane's Wrath \ncampaign."
    # Unban has an apostrophe and newline that get escaped.
    expected_unban_reason = "Needed for Kane&#x27;s Wrath campaign."

    # Run two bans to put multiple actions in the moderator notes.
    data_1 = dict(
        object_type="user",
        is_banned=True,
        object_id=str(cabal.id),
        note=ban_reason_1,
    )
    data_2 = {**data_1, "note": ban_reason_2}
    today = datetime.date.today()

    response_1 = mod_client_gdi.post(BASE_URL, data=data_1)
    response_2 = mod_client_gdi.post(BASE_URL, data=data_2)

    assert response_1.status_code == status.HTTP_200_OK
    assert response_2.status_code == status.HTTP_200_OK
    cabal.refresh_from_db()
    assert cabal.is_banned
    assert cabal.ban_reason == ban_reason_2
    assert cabal.ban_count == 2

    # Unban with a different mod.
    unban_data = dict(
        object_type="user",
        is_banned=False,
        object_id=str(cabal.id),
        note=unban_reason,
    )
    unban_response = mod_client_kane.post(BASE_URL, data=unban_data)

    assert unban_response.status_code == status.HTTP_200_OK

    cabal.refresh_from_db()
    assert not cabal.is_banned
    assert cabal.ban_reason is None
    assert cabal.ban_count == 2
    assert cabal.moderator_notes == (
        f"- Banned [{today.isoformat()}]: {ban_reason_1} -- by: '{mod_gdi.username}'\n"
        f"- Banned [{today.isoformat()}]: {ban_reason_2} -- by: '{mod_gdi.username}'\n"
        f"- Unbanned [{today.isoformat()}]: {expected_unban_reason} -- by: '{mod_kane.username}'\n"
    )


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
