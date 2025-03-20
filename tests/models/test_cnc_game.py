import pytest

from kirovy import exceptions, typing as t
from kirovy.models import CncGame, CncFileExtension


def test_cnc_game_url(db, settings):
    """Test that we generate the proper urls for logo and icon files."""
    ra2 = CncGame(full_name="Red Alert 2", slug="ra2")

    settings.STATIC_URL = "st/"
    settings.CNC_GAME_IMAGE_DIRECTORY = "gi/"
    assert ra2.icon_url == "/st/gi/ra2/ra2-icon.png"
    assert ra2.logo_url == "/st/gi/ra2/logo.png"


@pytest.mark.parametrize(
    "extension,expect_error",
    [
        ("mp3", False),
        ("mix123}", True),  # Errors because of the bracket.
        (".mix", True),  # Errors because the period is not alphanumeric.
        ("urm", False),
    ],
)
def test_cnc_extension_validator(db, extension, expect_error):
    """Test creating extensions and the extension validator."""

    def _make(ext: str) -> CncFileExtension:
        ext_obj = CncFileExtension(extension=ext)
        ext_obj.save()
        return ext_obj

    if expect_error:
        with pytest.raises(exceptions.InvalidFileExtension) as exc_info:
            _make(extension)
        assert extension in str(exc_info.value)
    else:
        cnc_extension = _make(extension)
        assert cnc_extension.extension == extension
        assert cnc_extension.extension_for_path == f".{extension}"


def test_cnc_game_extensions_set(db):
    """Test that the allowed extension set only shows extensions linked to the game."""
    extension_set = {"exe", "mp4", "mp3", "mp5"}
    cnc_extensions: t.List[CncFileExtension] = []
    for extension in extension_set:
        cnc_extension = CncFileExtension(extension=extension)
        cnc_extension.save()
        cnc_extensions.append(cnc_extension)

    cnc_game = CncGame(slug="yuri", full_name="yuri")
    cnc_game.save()
    cnc_game.allowed_extensions.add(*cnc_extensions)

    assert cnc_game.allowed_extensions_set == extension_set
