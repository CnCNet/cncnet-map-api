"""Tests for editing and moderating maps via ``PATCH /maps/<id>/``."""

from rest_framework import status

from kirovy.constants import api_codes
from kirovy.models import CncMap


def _url(cnc_map: CncMap) -> str:
    return f"/maps/{cnc_map.id}/"


def test_map_edit__owner_happy_path(create_cnc_map, create_cnc_map_category, client_user):
    """Map authors can finish an upload: name, description, categories, and publishing."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id, is_published=False)
    CncMap.objects.filter(id=cnc_map.id).update(incomplete_upload=True)
    koth = create_cnc_map_category("King of the Hill")

    response = client_user.patch(
        _url(cnc_map),
        data={
            "map_name": "Streets Of Gold 3",
            "description": "Now with more gold, and fewer streets.",
            "category_ids": [str(koth.id)],
            "is_published": True,
            "incomplete_upload": False,
        },
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    cnc_map.refresh_from_db()
    assert cnc_map.map_name == "Streets Of Gold 3"
    assert cnc_map.description == "Now with more gold, and fewer streets."
    assert list(cnc_map.categories.all()) == [koth]
    assert cnc_map.is_published
    assert not cnc_map.incomplete_upload
    assert cnc_map.last_modified_by_id == client_user.kirovy_user.id
    assert cnc_map.moderated_by_id is None, "Owners editing their own maps is not a moderation action."
    assert response.data["category_ids"] == [str(koth.id)]


def test_map_edit__other_users_map(create_cnc_map, create_kirovy_user, client_user):
    cnc_map = create_cnc_map(user_id=create_kirovy_user(username="Someone Else").id)

    response = client_user.patch(_url(cnc_map), data={"map_name": "Stolen"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    cnc_map.refresh_from_db()
    assert cnc_map.map_name != "Stolen"


def test_map_edit__anonymous(cnc_map, client_anonymous):
    response = client_anonymous.patch(_url(cnc_map), data={"map_name": "Vandalized"})

    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}
    cnc_map.refresh_from_db()
    assert cnc_map.map_name != "Vandalized"


def test_map_edit__banned_map(create_cnc_map, client_user):
    """Owners can't edit their maps after a ban. Don't let people destroy evidence."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id, is_banned=True)

    response = client_user.patch(_url(cnc_map), data={"description": "Nothing to see here, honest."})

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_map_edit__uneditable_fields(create_cnc_map, create_kirovy_user, client_user):
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)
    other_user = create_kirovy_user(username="Other")

    response = client_user.patch(_url(cnc_map), data={"cnc_user_id": str(other_user.id), "map_name": "Mine Now"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == api_codes.GenericApiCodes.CANNOT_UPDATE_FIELD
    assert response.data["additional"]["attempted"] == ["cnc_user"]
    cnc_map.refresh_from_db()
    assert cnc_map.cnc_user_id == client_user.kirovy_user.id
    assert cnc_map.map_name != "Mine Now"


def test_map_edit__is_reviewed_is_staff_only(create_cnc_map, client_user):
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)

    response = client_user.patch(_url(cnc_map), data={"is_reviewed": True})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    cnc_map.refresh_from_db()
    assert not cnc_map.is_reviewed


def test_map_edit__moderator_curates_and_hides(create_cnc_map, user, client_moderator, moderator):
    """Moderators can edit, curate, and hide (unpublish) other users' maps, and it's logged."""
    cnc_map = create_cnc_map(user_id=user.id, is_published=True)

    response = client_moderator.patch(
        _url(cnc_map), data={"is_reviewed": True, "is_published": False, "map_name": "Cleaned Up Name"}
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    cnc_map.refresh_from_db()
    assert cnc_map.is_reviewed
    assert not cnc_map.is_published
    assert cnc_map.map_name == "Cleaned Up Name"
    assert cnc_map.cnc_user_id == user.id, "Moderator edits must not change the owner."
    assert cnc_map.moderated_by_id == moderator.id
    assert "Edited" in cnc_map.moderator_notes
    assert "is_published, is_reviewed, map_name" in cnc_map.moderator_notes
    assert moderator.username in cnc_map.moderator_notes


def test_map_edit__put_not_allowed(cnc_map, client_user):
    response = client_user.put(_url(cnc_map), data={"map_name": "Whole New Map"})

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
