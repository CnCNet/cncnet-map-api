import pytest
from django.core import validators

from kirovy.models.cnc_map import CncMapFile


def test_cnc_map_create_model(game_yuri, extension_map, extension_mix):
    """Test creating a map with a bad and good file extension."""
    with pytest.raises(validators.ValidationError) as exc_info:
        CncMapFile(file_extension=extension_mix, cnc_game=game_yuri)
    assert extension_mix.extension in str(exc_info.value)

    allowed = CncMapFile(
        file_extension=extension_map, cnc_game=game_yuri, name="Streets of Gold"
    )
    assert allowed.file_extension.id == extension_map.id
