import pathlib
import zipfile
import io

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status

from kirovy import settings, typing as t
from kirovy.constants.api_codes import UploadApiCodes
from kirovy.models.cnc_map import CncMapImageFile
from kirovy.utils import file_utils
from kirovy.models import CncMap, CncMapFile, MapCategory
from kirovy.response import KirovyResponse
from kirovy.services.cnc_gen_2_services import CncGen2MapParser

_UPLOAD_URL = "/maps/upload/"
_CLIENT_URL = "/maps/client/upload/"


def test_map_file_upload_happy_path(client_user, file_map_desert, game_yuri, extension_map, tmp_media_root):
    response: KirovyResponse = client_user.post(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_yuri.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_201_CREATED

    uploaded_file_url: str = response.data["result"]["cnc_map_file"]
    uploaded_image_url: str = response.data["result"]["extracted_preview_file"]

    # We need to strip the url path off of the files,
    # then check the tmp directory to make sure the uploaded files were saved
    strip_media_url = f"/{settings.MEDIA_URL}"
    uploaded_file_path = pathlib.Path(tmp_media_root) / uploaded_file_url.lstrip(strip_media_url)
    uploaded_image = pathlib.Path(tmp_media_root) / uploaded_image_url.lstrip(strip_media_url)
    assert uploaded_file_path.exists()
    assert uploaded_image.exists()

    uploaded_file = UploadedFile(uploaded_file_path.open(mode="rb"))

    file_response = client_user.get(uploaded_file_url)
    image_response = client_user.get(uploaded_image_url)
    assert file_response.status_code == status.HTTP_200_OK
    assert image_response.status_code == status.HTTP_200_OK

    parser = CncGen2MapParser(uploaded_file)
    assert parser.ini.get("CnCNet", "ID") == str(response.data["result"]["cnc_map_id"])

    map_object = CncMap.objects.get(id=response.data["result"]["cnc_map_id"])
    file_object = CncMapFile.objects.get(cnc_map_id=map_object.id)
    image_object = CncMapImageFile.objects.get(cnc_map_id=map_object.id)

    assert map_object

    # Note: These won't match an md5 from the commandline because we add the ID to the map file.
    assert file_object.hash_md5 == file_utils.hash_file_md5(uploaded_file.open())
    file_map_desert.seek(0)
    assert file_object.hash_md5 != file_utils.hash_file_md5(file_map_desert.open())

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

    # Check the get endpoint returns the files.
    assert len(response_map["files"]) == 1
    assert response_map["files"][0]["id"] == str(file_object.id)
    assert response_map["files"][0]["file"].endswith(uploaded_file_url)

    # Check that the image was included
    assert len(response_map["images"]) == 1
    assert response_map["images"][0]["id"] == str(image_object.id)
    assert response_map["images"][0]["name"] == map_object.map_name
    assert response_map["images"][0]["file"].endswith(uploaded_image_url)
    assert response_map["images"][0]["is_extracted"] is True


def test_map_file_upload_banned_user(file_map_desert, game_yuri, client_banned):
    """Test that a banned user cannot upload a new map."""
    response = client_banned.post(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_yuri.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_map_file_upload_banned_map(banned_cheat_map, file_map_unfair, client_anonymous):
    """Test that an uploaded map will be rejected if the hash matches a banned one."""
    response = client_anonymous.post(
        _CLIENT_URL,
        {"file": file_map_unfair, "game": banned_cheat_map.cnc_game.slug},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == UploadApiCodes.DUPLICATE_MAP
    assert response.data["additional"]["existing_map_id"] == str(banned_cheat_map.id)
