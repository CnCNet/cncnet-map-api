import dataclasses
import datetime

from application.objects import CncnetUserInfo


def test_user_info_create_from_dict():
    def _date_to_str(dt: datetime.datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    created = datetime.datetime(2023, 9, 28, 11, 29, 36)
    data = {
        "id": 117,
        "name": "john",
        "email": "s117@oni.unsc.ueg.gov",
        "created_at": _date_to_str(created),
        "updated_at": None,
        "group": "S2",
        "ip_address_id": 123456,
        "email_verified": 1,
        "avatar_path": None,
        "avatar_upload_allowed": 0,
        "youtube_profile": "xX_headsh0tz_Xx",
        "twitch_profile": "",
        "alias": "Sierra 117",
        "ignored_field": "ignore me",
    }

    data_class = CncnetUserInfo(**data)

    assert data_class.id == data["id"]
    assert data_class.name == data["name"]
    assert data_class.email == data["email"]
    assert (
        data_class.created_at == created
    )  # should have converted tp datetime.datetime
    assert (
        data_class.updated_at is None
    )  # should skip conversion because it was None in the data dict.
    assert data_class.group == data["group"]
    assert data_class.ip_address_id == data["ip_address_id"]
    assert data_class.email_verified is True  # Should have converted from int.
    assert data_class.avatar_path is None
    assert data_class.avatar_upload_allowed is False
    assert data_class.discord_profile is None  # was not in data dict
    assert data_class.youtube_profile == data["youtube_profile"]
    assert data_class.twitch_profile == data["twitch_profile"]
    assert data_class.alias == data["alias"]
    assert not hasattr(data_class, "ignored_field")  # should have been filtered out
    assert "ignored_field" not in dataclasses.asdict(data_class).items()
