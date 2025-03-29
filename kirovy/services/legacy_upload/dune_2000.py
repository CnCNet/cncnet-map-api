"""
# README

Hello future traveler. If you are looking for info on formatting for Dune 2000 map files,
then feel free to use the info here.

Be warned though, this was mashed together from several archived wiki pages, various code repos,
and &mdash; at the time &mdash; 20-year-old forum threads. Many of these sources contradict each other in some way.

The information is, therefore, **not guaranteed** to be accurate.

At the time of writing, the `Dune 2000 mission editor <https://github.com/penev92/D2kMissionEditor>`_ is likely the most
authoritative and complete documentation of how these files work.

- Alex (2025)
"""

import struct
import zipfile
from functools import cached_property

from django.core.files.base import ContentFile

from kirovy import constants, typing as t
from kirovy.constants.api_codes import LegacyUploadApiCodes
from kirovy.exceptions import view_exceptions
from kirovy.services.cnc_gen_2_services import CncGen2MapParser
from kirovy.services.legacy_upload.base import LegacyMapServiceBase, ExpectedFile
from kirovy.utils import file_utils
from kirovy.utils.file_utils import ByteSized

__all__ = ["Dune2000LegacyMapService"]  # A lot of junk in this file, only export the map service.


class Dune2000LegacyMapService(LegacyMapServiceBase):
    game_slug = constants.GameSlugs.dune_2000
    ini_extensions = {".ini"}

    @cached_property
    def expected_files(self) -> t.List[ExpectedFile]:
        return [
            ExpectedFile(possible_extensions={".map"}, file_validator=dune_2000_map_validator, required=True),
            ExpectedFile(possible_extensions=self.ini_extensions, file_validator=ini_file_validator, required=True),
            ExpectedFile(possible_extensions={".mis"}, file_validator=mission_file_validator, required=False),
        ]


class Dune2000MapConstants:
    max_height = 128
    """Max height of a map in Dune 2000."""
    max_width = max_height
    """Max width of a map in Dune 2000."""
    header_bytes_size = 4  # 4 unsigned short bytes.
    """The size of a ``.map`` file header, in bytes."""
    min_width = 1
    min_height = min_width
    bytes_per_tile = 4  # [0] and [1] are the tile index. [2] and [3] are the special index
    """How many bytes define a tile/cell in a ``.map`` file.

    ``[0]`` and ``[1]`` are the tile index. ``[2]`` and ``[3]`` are the special index
    """
    width_index = 0
    """The byte that stores the map width in a ``.map`` file."""
    height_index = 1
    """The byte that stores the map height in a ``.map`` file."""
    tiles_start_index = height_index + 1
    min_tile_set_index = 0
    max_tile_set_index = 799
    """The maximum tile index for a tileset in Dune 2000"""
    min_special_set_index = 0
    max_special_set_index = 999
    """The maximum special tile index for a special tileset in Dune 2000"""
    byte_format = "<H"
    """unsigned short, little endian."""


def ini_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    """Backwards compatible file validator for Dune 2000 map INI files."""
    if ByteSized(zip_info.file_size) > ByteSized(mega=2):
        raise view_exceptions.KirovyValidationError(
            "INI file larger than expected.", code=LegacyUploadApiCodes.MAP_TOO_LARGE
        )

    # Reaching into the new map parsers is kind of dirty, but this legacy endpoint
    # is (hopefully) just to tide us over until we can migrate everyone to the new endpoints.
    if not CncGen2MapParser.is_text(file_content):
        raise view_exceptions.KirovyValidationError("No valid INI file.", code=LegacyUploadApiCodes.NO_VALID_MAP_FILE)


def dune_2000_map_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    """Backwards compatible file validator for Dune 2000's ``.map`` files.

    These are not to be confused with the zipped files. The ``.map`` file is a binary file
    with a header defining the map size, and an array of integers saying which tile image to use
    for a given cell on the map.

    `Archive link <https://web.archive.org/web/20150527200118/http://d2kplus.com/wiki/index.php?title=Map_Files>`_
    """
    file_content.seek(0)
    data = file_content.read()
    try:
        unpacked: t.List[[int]] = file_utils.flat_unpack("<H", data)
    except struct.error:
        raise view_exceptions.KirovyValidationError(
            "Map file invalid. Could not parse. This is a problem with your map, not the server.",
            code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE,
        )
    map_width = unpacked[Dune2000MapConstants.width_index]
    map_height = unpacked[Dune2000MapConstants.height_index]
    _validate_map_size(map_width, map_height)
    _validate_map_bytes_size(data, map_width, map_height)
    _validate_map_tile_indices(unpacked)


def _validate_map_size(map_width: int, map_height: int) -> None:
    """Validate that the map's size, in tiles, is within Dune 2000's bounds."""
    if map_width > Dune2000MapConstants.max_width or map_width < Dune2000MapConstants.min_width:
        raise view_exceptions.KirovyValidationError(
            f"Map width is invalid: {map_width=}", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )
    if map_height > Dune2000MapConstants.max_height or map_height < Dune2000MapConstants.min_height:
        raise view_exceptions.KirovyValidationError(
            f"Map height is invalid: {map_height=}", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )


def _validate_map_bytes_size(data: bytes, map_width: int, map_height: int) -> None:
    """Validate that the map file is the correct size, given its map height and width.

    - Each map cell is 4 bytes :attr:`kirovy.services.legacy_upload.dune_2000.Dune2000MapConstants.bytes_per_tile`.
    - The header is 4 bytes :attr:`kirovy.services.legacy_upload.dune_2000.Dune2000MapConstants.bytes_per_tile`

    The map byte size should be ``(map_height * width * cell_size) + header_size``
    """
    expected_size_bytes = (
        map_width * map_height * Dune2000MapConstants.bytes_per_tile
    ) + Dune2000MapConstants.header_bytes_size

    if expected_size_bytes != len(data):
        raise view_exceptions.KirovyValidationError(
            "Map tile size does not match map file size.", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )


def _validate_map_tile_indices(unpacked: t.List[int]) -> None:
    """Validate that all tiles in the map file are within the expected range for Dune 2000 tilesets."""
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


class MissionConstants:
    exact_bytes = 68_066
    """Dune 2000 ``.mis`` files must be **exactly** this size."""
    ulong_format = "<L"
    """Unsigned long, little-endian"""
    char_format = "B"
    """Unsigned char."""
    b_cash_start = 8
    """The byte that the starting cash config starts at."""
    b_cash_end = 39
    """The byte that the starting cash config stops at."""
    max_cash = 70_000
    """The maximum starting cash that a house can have in Dune."""
    max_tech_level = 9
    """The maximum tech level in Dune 2000."""
    b_tech_start = 0
    """The first byte storing house tech levels."""
    b_tech_end = 7
    """The final byte storing house tech levels."""
    b_tile_name_start = 66_968
    """The first byte containing the tile set name."""
    b_tile_name_end = 67_167
    """The final byte reserved for containing the tile set name.

    Tileset names have 200 bytes reserved, but the longest name in the game is <10.
    """
    b_tile_padding_starts = b_tile_name_start + 10
    """Every byte for the tileset name should be 0 after this point."""
    b_tile_data_name_starts = 67_168
    """The first byte containing the tile data name."""
    b_tile_data_padding_starts = b_tile_data_name_starts + 11
    """Every byte for the tile data name should be 0 after this point."""
    b_tile_data_name_ends = 67_175
    """The final byte reserved for containing the tile data name.

    Tile data names have 200 bytes reserved, but the longest name in the game is <10.
    """


def mission_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    """Backwards compatible file validator for Dune 2000 mission files."""
    file_content.seek(0)
    data = file_content.read()

    if len(data) != MissionConstants.exact_bytes:
        raise view_exceptions.KirovyValidationError(
            f"Mission file is the wrong size. Must by exactly {MissionConstants.exact_bytes} bytes."
        )

    try:
        _validate_mis_starting_cash(data)
        _validate_mis_tech_level(data)
        _validate_mis_tile_padding(data, MissionConstants.b_tile_padding_starts, MissionConstants.b_tile_name_end)
        _validate_mis_tile_padding(
            data, MissionConstants.b_tile_data_padding_starts, MissionConstants.b_tile_data_name_ends
        )
    except struct.error:
        raise view_exceptions.KirovyValidationError(
            "Mission file invalid. Could not parse. This is a problem with your mission, not the server.",
            code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE,
        )


def _validate_mis_tech_level(mis_data: bytes) -> None:
    tech_bytes = mis_data[MissionConstants.b_tech_start : MissionConstants.b_tech_end + 1]
    tech_unpacked: t.List[int] = file_utils.flat_unpack(MissionConstants.char_format, tech_bytes)
    for i, house_tech in enumerate(tech_unpacked):
        if house_tech > MissionConstants.max_tech_level:
            raise view_exceptions.KirovyValidationError(
                f"Mission file has too high of a tech level for house {i+1}",
                code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE,
            )


def _validate_mis_starting_cash(mis_data: bytes) -> None:
    # Starting cash is stored as four uint32 bytes. A uint32 is four bytes.
    money_bytes = mis_data[MissionConstants.b_cash_start : MissionConstants.b_cash_end + 1]
    money_unpacked: t.List[int] = file_utils.flat_unpack(MissionConstants.ulong_format, money_bytes)
    for i, house_cash in enumerate(money_unpacked):
        if house_cash > MissionConstants.max_cash:
            raise view_exceptions.KirovyValidationError(
                f"Mission file has too much starting cash for house {i+1}",
                code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE,
            )


def _validate_mis_tile_padding(mis_data: bytes, padding_start: int, stop: int) -> None:
    """Validate the tileset name length.

    The Dune 2000 tileset name reserves 200 bytes for the string but only uses ten of them.

    `Archive wiki link <https://web.archive.org/web/20150527200312/http://d2kplus.com/wiki/index.php?title=Tile_Sets>`_

    :param mis_data:
        The mis file bytes
    :param padding_start:
        The first byte in tile name or tile set that should be 0.
    :param stop:
        The final byte index for the allocated tile name/data.
    """
    # +1 because ``[n:n]`` is up-to-but-not-including.
    padding_bytes = mis_data[padding_start : stop + 1]
    padding_unpacked = file_utils.flat_unpack(MissionConstants.char_format, padding_bytes)
    if not all([c == 0 for c in padding_unpacked]):
        raise view_exceptions.KirovyValidationError(
            "Tileset name is too long", code=LegacyUploadApiCodes.MAP_FAILED_TO_PARSE
        )
