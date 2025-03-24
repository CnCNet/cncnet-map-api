import hashlib
import pathlib
import zipfile
import io

import pytest
from django.core.files.base import ContentFile
from django.http import FileResponse
from rest_framework import status

from kirovy.models import CncGame, CncMapFile
from kirovy.response import KirovyResponse
from kirovy.utils import file_utils


@pytest.mark.parametrize("game_slug", ["td", "ra", "ts", "dta", "yr", "d2"])
def test_map_download_backwards_compatible(
    create_cnc_map, create_cnc_map_file, file_map_desert, client_anonymous, game_slug
):
    """Test that we can properly fetch a map with the backwards compatible endpoints."""
    game = CncGame.objects.get(slug__iexact=game_slug)
    cnc_map = create_cnc_map(is_temporary=True, cnc_game=game)
    map_file = create_cnc_map_file(file_map_desert, cnc_map)

    response: FileResponse = client_anonymous.get(f"/{game_slug}/{map_file.hash_sha1}")

    assert response.status_code == status.HTTP_200_OK
    file_content_io = io.BytesIO(response.getvalue())
    zip_file = zipfile.ZipFile(file_content_io)
    assert zip_file

    map_from_zip = zip_file.read(f"{map_file.hash_sha1}.map")
    downloaded_map_hash = hashlib.sha1(map_from_zip).hexdigest()
    assert downloaded_map_hash == map_file.hash_sha1


# def test_map_upload_dune2k_backwards_compatible(
#     client_anonymous, rename_file_for_legacy_upload, file_map_dune2k_valid, game_dune2k
# ):
#     url = "/upload"
#     file = rename_file_for_legacy_upload(file_map_dune2k_valid)
#
#     response: KirovyResponse = client_anonymous.post(
#         url, {"file": file, "game": game_dune2k.slug}, format="multipart", content_type=None
#     )
#
#     assert response.status_code == status.HTTP_200_OK


def test_map_upload_single_file_backwards_compatible(
    client_anonymous,
    zip_map_for_legacy_upload,
    file_map_desert,
    file_map_ts_woodland_hills,
    game_yuri,
    game_tiberian_sun,
):
    game_map_name = [
        (game_yuri, file_map_desert, "desert"),
        (game_tiberian_sun, file_map_ts_woodland_hills, "Woodland Hills"),
    ]
    url = "/upload"
    for game, file_map, map_name in game_map_name:
        upload_file, file_sha1 = zip_map_for_legacy_upload(file_map)
        upload_response: KirovyResponse = client_anonymous.post(
            url, {"file": upload_file, "game": game.slug}, format="multipart", content_type=None
        )

        assert upload_response.status_code == status.HTTP_200_OK

        response: FileResponse = client_anonymous.get(f"/{game.slug}/{file_sha1}")
        assert response.status_code == status.HTTP_200_OK

        file_content_io = io.BytesIO(response.getvalue())
        zip_file = zipfile.ZipFile(file_content_io)
        assert zip_file

        map_from_zip = zip_file.read(f"{file_sha1}.map")
        downloaded_map_hash = hashlib.sha1(map_from_zip).hexdigest()
        assert downloaded_map_hash == file_sha1

        cnc_map_file: CncMapFile = CncMapFile.objects.find_legacy_map_by_sha1(file_sha1)

        assert cnc_map_file
        assert cnc_map_file.cnc_game_id == game.id
        assert cnc_map_file.cnc_map.map_name == map_name
