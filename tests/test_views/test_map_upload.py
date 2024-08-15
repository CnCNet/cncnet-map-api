import pathlib

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status

from kirovy.services.cnc_gen_2_services import CncGen2MapParser

_UPLOAD_URL = "/maps/upload/"


def test_map_file_upload_happy_path(
    client_user, file_map_desert, game_yuri, extension_map, tmp_media_root
):
    # TODO: Finish the tests.
    response = client_user.post(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_yuri.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_201_CREATED
    uploaded_file = pathlib.Path(tmp_media_root) / response.data["result"][
        "cnc_map_file"
    ].lstrip("/")
    uploaded_image = pathlib.Path(tmp_media_root) / response.data["result"][
        "extracted_preview_file"
    ].lstrip("/")
    assert uploaded_file.exists()
    assert uploaded_image.exists()

    parser = CncGen2MapParser(UploadedFile(open(uploaded_file, "rb")))
    assert parser.ini.get("CnCNet", "ID") == str(response.data["result"]["cnc_map_id"])
