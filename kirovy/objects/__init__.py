import datetime
from dataclasses import dataclass, field, fields, Field

from kirovy import typing as t


@dataclass
class CncnetUserInfo:
    id: int = field()
    name: str = field()
    email: str = field()
    created_at: datetime.datetime = field()
    updated_at: datetime.datetime = field()
    group: str = field()
    ip_address_id: int = field()
    email_verified: bool = field()
    avatar_path: t.Optional[str] = field()
    avatar_upload_allowed: bool = field()
    discord_profile: str = field()
    youtube_profile: str = field()
    twitch_profile: str = field()
    alias: str = field()

    def __init__(self, **kwargs):
        for user_field in fields(self):
            value = kwargs.get(user_field.name)
            if value is None:
                setattr(self, user_field.name, None)
            else:
                self._convert_and_set(value, user_field)

    def _convert_and_set(self, value: t.Any, user_field: Field) -> None:
        """Convert any relevant types, and set the class attrs.

        :param value:
            The value from CncNet.
        :param user_field:
            The field data from the class definition.
        """
        if user_field.type is datetime.datetime:
            setattr(self, user_field.name, datetime.datetime.fromisoformat(value))
        elif user_field.type is bool:
            setattr(self, user_field.name, bool(value))
        else:
            setattr(self, user_field.name, value)
