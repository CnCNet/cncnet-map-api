import pathlib
import subprocess
from hashlib import md5

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status

from kirovy import settings
from kirovy.models import CncMap, CncMapFile, MapCategory
from kirovy.services.cnc_gen_2_services import CncGen2MapParser

_UPLOAD_URL = "/maps/upload/"


def test_map_file_upload_happy_path(client_user, file_map_desert, game_yuri, extension_map, tmp_media_root):
    response = client_user.post(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_yuri.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_201_CREATED

    uploaded_file_url: str = response.data["result"]["cnc_map_file"]
    uploaded_image_url: str = response.data["result"]["extracted_preview_file"]
    strip_media_url = f"/{settings.MEDIA_URL}"
    uploaded_file = pathlib.Path(tmp_media_root) / uploaded_file_url.lstrip(strip_media_url)
    uploaded_image = pathlib.Path(tmp_media_root) / uploaded_image_url.lstrip(strip_media_url)
    assert uploaded_file.exists()
    assert uploaded_image.exists()

    file_response = client_user.get(uploaded_file_url)
    image_response = client_user.get(uploaded_image_url)
    assert file_response.status_code == status.HTTP_200_OK
    assert image_response.status_code == status.HTTP_200_OK

    parser = CncGen2MapParser(UploadedFile(open(uploaded_file, "rb")))
    assert parser.ini.get("CnCNet", "ID") == str(response.data["result"]["cnc_map_id"])

    map_object = CncMap.objects.get(id=response.data["result"]["cnc_map_id"])
    file_object = CncMapFile.objects.get(cnc_map_id=map_object.id)

    assert map_object

    # Note: These won't match an md5 from the commandline because we add the ID to the map file.
    assert file_object.hash_md5 == md5(open(uploaded_file, "rb").read()).hexdigest()
    file_map_desert.seek(0)
    assert file_object.hash_md5 != md5(file_map_desert.read()).hexdigest()

    get_response = client_user.get(f"/maps/{map_object.id}/")

    assert get_response.status_code == status.HTTP_200_OK
    response_map = get_response.data["result"]

    # A lot of these will break if you change the desert.map file.
    assert response_map["cnc_user_id"] == str(client_user.kirovy_user.id)
    assert response_map["map_name"] == "desert", "Should match the name in the map file."
    assert response_map["cnc_game_id"] == str(game_yuri.id)
    assert response_map["category_ids"] == [
        str(MapCategory.objects.get(name__iexact="standard").id),
    ]
    assert not response_map["is_published"], "Newly uploaded, unrefined, maps should default to unpublished."
    assert not response_map["is_temporary"], "Maps uploaded via a signed in user shouldn't be marked as temporary."
    assert not response_map["is_reviewed"], "Maps should not default to being reviewed."
    assert not response_map["is_banned"], "Happy path maps should not be banned on upload."
    assert response_map["legacy_upload_date"] is None, "Non legacy maps should never have this field."
    assert response_map["id"] == str(map_object.id)
