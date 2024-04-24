import pathlib
from urllib import parse

from rest_framework import status

_UPLOAD_URL = "/maps/upload/"


def test_map_file_upload_happy_path(
    client_user, file_map_desert, game_yuri, extension_map
):
    # TODO: Finish the tests.
    file_name = parse.quote_plus(pathlib.Path(file_map_desert.name).name)
    response = client_user.post(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_yuri.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_201_CREATED
