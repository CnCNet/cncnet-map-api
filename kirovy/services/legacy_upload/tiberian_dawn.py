import zipfile
from functools import cached_property

from django.core.files.base import ContentFile

from kirovy import constants, typing as t
from kirovy.constants.api_codes import LegacyUploadApiCodes
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.services.cnc_gen_2_services import CncGen2MapParser
from kirovy.services.legacy_upload.base import ExpectedFile, LegacyMapServiceBase
from kirovy.utils.file_utils import ByteSized

__all__ = ["TiberianDawnLegacyMapService"]


class TiberianDawnLegacyMapService(LegacyMapServiceBase):
    game_slug = constants.GameSlugs.tiberian_dawn
    ini_extensions = {".ini"}

    @cached_property
    def expected_files(self) -> t.List[ExpectedFile]:
        return [
            ExpectedFile(possible_extensions=self.ini_extensions, file_validator=_ini_file_validator, required=True),
            ExpectedFile(possible_extensions={".bin"}, file_validator=_bin_file_validator, required=True),
        ]


def _ini_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    if ByteSized(file_content.size) > ByteSized(kilo=128):
        raise KirovyValidationError(
            "File too large. The bin and ini file can each be a max of 128KB",
            LegacyUploadApiCodes.MAP_TOO_LARGE,
        )

    # Reaching into the new map parsers is kind of dirty, but this legacy endpoint
    # is (hopefully) just to tide us over until we can migrate everyone to the new endpoints.
    if not CncGen2MapParser.is_text(file_content):
        raise KirovyValidationError("No valid map file.", code=LegacyUploadApiCodes.NO_VALID_MAP_FILE)


def _bin_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    if file_content.size != 8192:
        raise KirovyValidationError(
            "Bin files must be exactly 8192 bytes",
            LegacyUploadApiCodes.NO_VALID_MAP_FILE,
        )
