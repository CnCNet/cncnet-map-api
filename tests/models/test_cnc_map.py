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


def test_cnc_map_generate_upload_to(
    game_yuri, extension_map, file_map_desert, cnc_map, settings
):
    """Test that we generate the correct upload path for a map file.

    This test will fail if you alter the initial migrations.
    """
    settings.CNC_MAP_DIRECTORY = (
        "worlds"  # Change default to check that the settings control the upload path.
    )
    expected_path = pathlib.Path(
        settings.MEDIA_ROOT,
        "yr",
        "worlds",
        cnc_map.id.hex,
        f"yr_{cnc_map.id.hex}_v01.map",
    )
    saved_map = CncMapFile(
        height=117,  # doesn't matter for this test.
        width=117,  # doesn't matter for this test.
        file=file_map_desert,
        file_extension=extension_map,
        cnc_map=cnc_map,
        cnc_game=game_yuri,
        name=cnc_map.generate_versioned_name_for_file(),
    )
    saved_map.save()
    saved_map.refresh_from_db()

    assert saved_map.file.path == str(expected_path)


def test_cnc_map_version(game_yuri, extension_map, file_map_valid, cnc_map):
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
    # Make sure subsequent saves don't blow away the version.
    # map file models shouldn't be edited after upload, but check anyway.
    map2.height = 117
    map2.save()
    assert map2.version == 2

    assert pathlib.Path(map2.file.path).parent == pathlib.Path(map1.file.path).parent
