import io
import struct
import zipfile
from functools import cached_property

from django.core.files.base import ContentFile

from kirovy import constants, typing as t
from kirovy.constants.api_codes import LegacyUploadApiCodes
from kirovy.exceptions import view_exceptions
from kirovy.services.cnc_gen_2_services import CncGen2MapParser
from kirovy.services.legacy_upload.base import LegacyMapServiceBase, ExpectedFile
from kirovy.utils.file_utils import ByteSized


class Dune2000MapConstants:
    max_height = 128
    max_width = max_height
    header_bytes_size = 4  # 4 unsigned short bytes.
    min_width = 1
    min_height = min_width
    bytes_per_tile = 4  # [0] and [1] are the tile index. [2] and [3] are the special index
    width_index = 0
    height_index = 1
    tiles_start_index = height_index + 1
    max_tile_set_index = 799
    min_tile_set_index = 0
    max_special_set_index = 999
    min_special_set_index = 0


class MissionConstants:
    max_bytes = 68_066
    int_format = "<L"
    """Unsigned long, little-endian"""


def ini_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    if ByteSized(zip_info.file_size) > ByteSized(mega=2):
        raise view_exceptions.KirovyValidationError(
            "INI file larger than expected.", code=LegacyUploadApiCodes.MAP_TOO_LARGE
        )

    # Reaching into the new map parsers is kind of dirty, but this legacy endpoint
    # is (hopefully) just to tide us over until we can migrate everyone to the new endpoints.
    if not CncGen2MapParser.is_text(file_content):
        raise view_exceptions.KirovyValidationError("No valid INI file.", code=LegacyUploadApiCodes.NO_VALID_MAP_FILE)


def dune_2000_map_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    file_content.seek(0)
    data = file_content.read()
    # "<H" means "unsigned short, little endian.
    try:
        unpacked: t.List[[int]] = [x[0] for x in struct.iter_unpack("<H", data)]
    except struct.error:
        raise view_exceptions.KirovyValidationError(
            "Map file invalid. Could not parse. This is a problem with your map, not the server.",
            code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE,
        )
    map_width = unpacked[Dune2000MapConstants.width_index]
    map_height = unpacked[Dune2000MapConstants.height_index]
    _validate_map_size(map_width, map_height)
    _validate_map_bytes_size(data, map_width, map_height)
    _validate_tile_indices(unpacked)


def _validate_map_size(map_width: int, map_height: int) -> None:
    if map_width > Dune2000MapConstants.max_width or map_width < Dune2000MapConstants.min_width:
        raise view_exceptions.KirovyValidationError(
            f"Map width is invalid: {map_width=}", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )
    if map_height > Dune2000MapConstants.max_height or map_height < Dune2000MapConstants.min_height:
        raise view_exceptions.KirovyValidationError(
            f"Map height is invalid: {map_height=}", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )


def _validate_map_bytes_size(data: bytes, map_width: int, map_height: int) -> None:
    expected_size_bytes = (
        map_width * map_height * Dune2000MapConstants.bytes_per_tile
    ) + Dune2000MapConstants.header_bytes_size

    if expected_size_bytes != len(data):
        raise view_exceptions.KirovyValidationError(
            "Map tile size does not match map file size.", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )


def _validate_tile_indices(unpacked: t.List[int]) -> None:
    tile_index = Dune2000MapConstants.tiles_start_index
    while tile_index < len(unpacked):
        tile = unpacked[tile_index]
        if tile > Dune2000MapConstants.max_tile_set_index or tile < Dune2000MapConstants.min_tile_set_index:
            raise view_exceptions.KirovyValidationError("Invalid tile", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE)

        special = unpacked[tile + 1]
        if special > Dune2000MapConstants.max_special_set_index or special < Dune2000MapConstants.min_special_set_index:
            raise view_exceptions.KirovyValidationError(
                "Invalid special tile", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
            )

        tile_index += 2


class Dune2000LegacyMapService(LegacyMapServiceBase):
    game_slug = constants.GameSlugs.dune_2000
    ini_extensions = {".ini"}

    @cached_property
    def expected_files(self) -> t.List[ExpectedFile]:
        return [
            ExpectedFile(possible_extensions={".map"}, file_validator=dune_2000_map_validator, required=True),
            ExpectedFile(possible_extensions=self.ini_extensions, file_validator=ini_file_validator, required=True),
            ExpectedFile(possible_extensions={".mis"}, file_validator=ini_file_validator, required=False),
        ]
