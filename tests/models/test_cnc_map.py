import pathlib

import pytest
from django.core import validators

from kirovy.models.cnc_map import CncMapFile, CncMap, MapCategory


def test_cnc_map_invalid_file_extension(
    game_yuri, extension_map, extension_mix, cnc_map
):
    """Test creating a map with a non-map file extension is rejected."""
    with pytest.raises(validators.ValidationError) as exc_info:
        CncMapFile(
            file_extension=extension_mix, cnc_game=game_yuri, cnc_map=cnc_map
        ).save()
    assert extension_mix.extension in str(exc_info.value)


def test_cnc_map_version(
    game_yuri, extension_map, extension_mix, file_map_valid, cnc_map
):
    """Test saving two map files to one map will increment the version and place both files in the same directory."""
    map1 = CncMapFile(
        height=10,
        width=10,
        file=file_map_valid,
        file_extension=extension_map,
        cnc_map=cnc_map,
        cnc_game=game_yuri,
    )
    map1.save()
    map1.refresh_from_db()

    assert map1.version == 1

    map2 = CncMapFile(
        height=10,
        width=10,
        file=file_map_valid,
        file_extension=extension_map,
        cnc_map=cnc_map,
        cnc_game=game_yuri,
    )
    map2.save()
    map2.refresh_from_db()

    assert map2.version == 2

    assert pathlib.Path(map2.file.path).parent == pathlib.Path(map1.file.path).parent
