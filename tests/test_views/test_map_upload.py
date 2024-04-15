import pathlib
from urllib import parse

from rest_framework import status

_UPLOAD_URL = "/maps/upload/"


def test_map_file_upload_happy_path(client_user, file_map_desert):
    # TODO: Finish the tests.
    file_name = parse.quote_plus(pathlib.Path(file_map_desert.name).name)
    response = client_user.post(
        f"{_UPLOAD_URL}{file_name}/",
        {"file": file_map_desert},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_200_OK
