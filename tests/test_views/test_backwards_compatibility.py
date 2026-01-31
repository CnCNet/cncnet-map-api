import hashlib
import pathlib
import zipfile
import io

import pytest
from django.http import FileResponse
from rest_framework import status

from kirovy import typing as t
from kirovy.models import CncGame, CncMapFile, CncMap
from kirovy.response import KirovyResponse

if t.TYPE_CHECKING:
    from tests.fixtures.common_fixtures import KirovyClient


@pytest.mark.parametrize("game_slug", ["td", "ra", "ts", "dta", "yr", "d2"])
def test_map_download_backwards_compatible(
    create_cnc_map, create_cnc_map_file, file_map_desert, client_anonymous, game_slug
):
    """Test that we can properly fetch a map with the backwards compatible endpoints."""
    game = CncGame.objects.get(slug__iexact=game_slug)
    cnc_map: CncMap = create_cnc_map(is_temporary=True, cnc_game=game, is_mapdb1_compatible=True)
    map_file = create_cnc_map_file(file_map_desert, cnc_map, zip_for_legacy=True)

    response: FileResponse = client_anonymous.get(f"/{game_slug}/{map_file.hash_sha1}.zip")

    assert response.status_code == status.HTTP_200_OK
    file_content_io = io.BytesIO(response.getvalue())
    zip_file = zipfile.ZipFile(file_content_io)
    assert zip_file

    map_from_zip = zip_file.read(zip_file.infolist()[0])
    downloaded_map_hash = hashlib.sha1(map_from_zip).hexdigest()
    assert downloaded_map_hash == map_file.hash_sha1


def test_map_upload_dune2k_backwards_compatible(client_anonymous, file_map_dune2k, game_dune2k):
    url = "/upload"
    sha1 = "f9270d1e17e832a694dcd8c07e3acbb96a578a18"
    name = "Ornithopter Fringe"

    response: KirovyResponse = client_anonymous.post(
        url, {"file": file_map_dune2k, "game": game_dune2k.slug}, format="multipart", content_type=None
    )

    assert response.status_code == status.HTTP_200_OK

    _download_and_check_hash(client_anonymous, sha1, game_dune2k, name, [".map", ".ini"])


def test_map_upload_tiberian_dawn_backwards_compatible(client_anonymous, file_map_tiberian_dawn, game_tiberian_dawn):
    url = "/upload"
    sha1 = "18972a7372424bb456684f6e45119a5579042898"
    name = "[CHEM] Red Zone Rampage test map"

    response: KirovyResponse = client_anonymous.post(
        url, {"file": file_map_tiberian_dawn, "game": game_tiberian_dawn.slug}, format="multipart", content_type=None
    )

    assert response.status_code == status.HTTP_200_OK

    _download_and_check_hash(client_anonymous, sha1, game_tiberian_dawn, name, [".ini", ".bin"])


def test_map_upload_single_file_backwards_compatible(
    client_anonymous,
    zip_map_for_legacy_upload,
    file_map_desert,
    file_map_ts_woodland_hills,
    file_map_ra_d_day,
    file_map_dta_peace_and_war,
    game_yuri,
    game_tiberian_sun,
    game_dawn_of_the_tiberium_age,
    game_red_alert,
):
    """Test uploads for backwards compatible map files that only have a map file in the zip."""
    game_map_name = [
        (game_yuri, file_map_desert, "desert"),
        (game_tiberian_sun, file_map_ts_woodland_hills, "Woodland Hills"),
        (game_red_alert, file_map_ra_d_day, "D Day"),
        (game_dawn_of_the_tiberium_age, file_map_dta_peace_and_war, "Peace And War"),
    ]
    url = "/upload"
    for game, file_map, map_name in game_map_name:
        original_extension = pathlib.Path(file_map.name).suffix
        upload_file, file_sha1 = zip_map_for_legacy_upload(file_map)
        upload_response: KirovyResponse = client_anonymous.post(
            url, {"file": upload_file, "game": game.slug}, format="multipart", content_type=None, REMOTE_ADDR="2.2.2.2"
        )

        assert upload_response.status_code == status.HTTP_200_OK
        assert upload_response.data["result"]["download_url"] == f"/{game.slug}/{file_sha1}.zip"

        _download_and_check_hash(
            client_anonymous, file_sha1, game, map_name, [original_extension], ip_address="2.2.2.2"
        )


def _download_and_check_hash(
    client: "KirovyClient",
    file_sha1: str,
    game: CncGame,
    expected_map_name: str,
    extensions_to_check: t.List[str],
    ip_address: str | None = None,
):
    response: FileResponse = client.get(f"/{game.slug}/{file_sha1}.zip")
    assert response.status_code == status.HTTP_200_OK
    file_content_io = io.BytesIO(response.getvalue())
    zip_file = zipfile.ZipFile(file_content_io)
    assert zip_file
    for extension in extensions_to_check:
        map_from_zip = zip_file.read(f"{file_sha1}{extension}")
        assert map_from_zip

    cnc_map_file: CncMapFile = CncMapFile.objects.find_legacy_map_by_sha1(file_sha1, game.id)
    assert cnc_map_file
    assert cnc_map_file.cnc_game_id == game.id
    assert cnc_map_file.cnc_map.map_name == expected_map_name
    if ip_address:
        assert cnc_map_file.ip_address == ip_address
