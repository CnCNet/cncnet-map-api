import pytest

from kirovy import exceptions
from kirovy.services import MapParserService


def test_map_parser_service__is_binary(file_binary):
    assert MapParserService.is_binary(file_binary)
    assert not MapParserService.is_text(file_binary)


def test_map_parser_service__is_text(file_map_valid):
    assert MapParserService.is_text(file_map_valid)
    assert not MapParserService.is_binary(file_map_valid)


def test_map_parser_service__validate(file_binary):
    """Test that binary files fail validation."""
    with pytest.raises(exceptions.InvalidMimeType) as exc_info:
        MapParserService(file_binary)

    assert MapParserService.ErrorMsg.NO_BINARY in str(exc_info.value)


def test_map_parser_service__fails_parse(file_map_cant_parse):
    """Test that we raise an error when a text file can't be parsed as INI."""
    with pytest.raises(exceptions.InvalidMapFile) as exc_info:
        MapParserService(file_map_cant_parse)

    assert MapParserService.ErrorMsg.CORRUPT_MAP in str(exc_info.value)


def test_map_parser_service__fails_missing_sections(file_map_missing_sections):
    """Test that an error is raised when a map is missing required sections."""
    with pytest.raises(exceptions.InvalidMapFile) as exc_info:
        MapParserService(file_map_missing_sections)

    assert MapParserService.ErrorMsg.MISSING_INI in str(exc_info.value)

    # Make sure we only return sections that are missing.
    assert "Basic" not in exc_info.value.params["missing"]
    # Make sure unrelated sections from the map file don't show up.
    assert "Alliance" not in exc_info.value.params["missing"]
