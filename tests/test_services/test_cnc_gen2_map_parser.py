import pathlib

import pytest

from kirovy import exceptions
from kirovy.services.cnc_gen_2_services import CncGen2MapParser, CncGen2MapSections


def test_map_parser_service__is_binary(file_binary):
    assert CncGen2MapParser.is_binary(file_binary)
    assert not CncGen2MapParser.is_text(file_binary)


def test_map_parser_service__is_text(file_map_valid):
    assert CncGen2MapParser.is_text(file_map_valid)
    assert not CncGen2MapParser.is_binary(file_map_valid)


def test_map_parser_service__validate(file_binary):
    """Test that binary files fail validation."""
    with pytest.raises(exceptions.InvalidMimeType) as exc_info:
        CncGen2MapParser(file_binary)

    assert CncGen2MapParser.ErrorMsg.NO_BINARY in str(exc_info.value)


def test_map_parser_service__fails_parse(file_map_cant_parse):
    """Test that we raise an error when a text file can't be parsed as INI."""
    with pytest.raises(exceptions.InvalidMapFile) as exc_info:
        CncGen2MapParser(file_map_cant_parse)

    assert CncGen2MapParser.ErrorMsg.CORRUPT_MAP in str(exc_info.value)


def test_map_parser_service__fails_missing_sections(file_map_missing_sections):
    """Test that an error is raised when a map is missing required sections."""
    with pytest.raises(exceptions.InvalidMapFile) as exc_info:
        CncGen2MapParser(file_map_missing_sections)

    assert CncGen2MapParser.ErrorMsg.MISSING_INI in str(exc_info.value)

    # Make sure we only return sections that are missing.
    assert "Basic" not in exc_info.value.params["missing"]
    # Make sure unrelated sections from the map file don't show up.
    assert "Alliance" not in exc_info.value.params["missing"]


def test_map_service_can_extract_preview(
    file_map_valid, file_map_snow, file_map_desert, tmp_media_root
):
    # The width and height come from the fixture files.
    maps = [
        (file_map_valid, 160, 80),
        (file_map_snow, 66, 43),
        (file_map_desert, 246, 72),
    ]
    for map_file, width, height in maps:
        map_service = CncGen2MapParser(map_file)
        img = map_service.extract_preview()

        assert img is not None
        assert img.width == width
        assert img.height == height

        assert (
            map_service.ini.get(CncGen2MapSections.PREVIEW, "Size")
            == f"0,0,{width},{height}"
        )
        filename = pathlib.Path(map_file.name).stem
        img.save(tmp_media_root / f"{filename}.bmp", format="bmp", bitmap_format="bmp")

    assert True
