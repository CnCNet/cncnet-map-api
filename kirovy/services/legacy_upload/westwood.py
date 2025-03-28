from functools import cached_property

from kirovy import constants, typing as t
from kirovy.services.legacy_upload.base import LegacyMapServiceBase, ExpectedFile, default_map_file_validator


class YurisRevengeLegacyMapService(LegacyMapServiceBase):
    ini_extensions = {".map", ".yro", ".yrm"}
    game_slug = constants.GameSlugs.yuris_revenge

    @cached_property
    def expected_files(self) -> t.List[ExpectedFile]:
        return [
            ExpectedFile(
                possible_extensions=self.ini_extensions, file_validator=default_map_file_validator, required=True
            )
        ]
