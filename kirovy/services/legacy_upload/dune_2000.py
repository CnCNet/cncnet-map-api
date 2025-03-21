from kirovy import constants
from kirovy.services.legacy_upload.base import LegacyMapServiceBase


class Dune2000LegacyMapService(LegacyMapServiceBase):
    game_slug = constants.GameSlugs.dune_2000
