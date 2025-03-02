import typing

from django.db.models import UUIDField, Model

from .cnc_game import CncGame, CncFileExtension
from .cnc_map import CncMap, CncMapFile, MapCategory
from .cnc_user import CncUser
from .file_base import CncNetFileBaseModel
from .map_preview import MapPreview


class SupportsBan(typing.Protocol):
    def set_ban(self, is_banned: bool, banned_by: CncUser) -> None:
        ...
