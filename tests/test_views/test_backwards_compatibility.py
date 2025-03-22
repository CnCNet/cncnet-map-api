import hashlib
import pathlib
import zipfile
import io

import pytest
from django.core.files.base import ContentFile
from django.http import FileResponse
from rest_framework import status

from kirovy.models import CncGame
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


def test_map_upload_yuri_backwards_compatible(client_anonymous, file_map_desert, game_yuri):
    url = "/upload"
    file_sha1 = file_utils.hash_file_sha1(file_map_desert)
    extension = pathlib.Path(file_map_desert.name).suffix
    zip_bytes = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_bytes, mode="w")
    zip_file.writestr(file_map_desert.name, file_map_desert.read())
    zip_file.close()
    zip_bytes.seek(0)
    upload_file = ContentFile(zip_bytes.read(), f"{file_sha1}.zip")

    upload_response: KirovyResponse = client_anonymous.post(
        url, {"file": upload_file, "game": game_yuri.slug}, format="multipart", content_type=None
    )

    assert upload_response.status_code == status.HTTP_200_OK

    response: FileResponse = client_anonymous.get(f"/{game_yuri.slug}/{file_sha1}")
    assert response.status_code == status.HTTP_200_OK

    file_content_io = io.BytesIO(response.getvalue())
    zip_file = zipfile.ZipFile(file_content_io)
    assert zip_file

    map_from_zip = zip_file.read(f"{file_sha1}.map")
    downloaded_map_hash = hashlib.sha1(map_from_zip).hexdigest()
    assert downloaded_map_hash == file_sha1
