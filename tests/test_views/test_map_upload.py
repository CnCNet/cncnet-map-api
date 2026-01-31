from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse
from rest_framework import status

from kirovy.constants.api_codes import UploadApiCodes, FileUploadApiCodes
from kirovy.models.cnc_map import CncMapImageFile
from kirovy.objects import ui_objects
from kirovy.objects.ui_objects import ResultResponseData
from kirovy.utils import file_utils
from kirovy.models import CncMap, CncMapFile, MapCategory, CncGame
from kirovy.response import KirovyResponse
from kirovy.services.cnc_gen_2_services import CncGen2MapParser

_UPLOAD_URL = "/maps/upload/"
_CLIENT_URL = "/maps/client/upload/"


def test_map_file_upload_happy_path(
    client_user, file_map_desert, game_uploadable, extension_map, tmp_media_root, get_file_path_for_uploaded_file_url
):
    """Test uploading a map file via the UI endpoint."""
    response = client_user.post_file(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_uploadable.id)},
        HTTP_X_FORWARDED_FOR="117.117.117.117",
    )

    assert response.status_code == status.HTTP_201_CREATED

    uploaded_file_url: str = response.data["result"]["cnc_map_file"]
    uploaded_image_url: str = response.data["result"]["extracted_preview_file"]

    # We need to check the tmp directory to make sure the uploaded files were saved
    uploaded_file_path = get_file_path_for_uploaded_file_url(uploaded_file_url)
    uploaded_image = get_file_path_for_uploaded_file_url(uploaded_image_url)
    assert uploaded_file_path.exists()
    assert uploaded_image.exists()

    uploaded_file = UploadedFile(uploaded_file_path.open(mode="rb"))

    file_response: FileResponse = client_user.get_file(uploaded_file_url)
    image_response: FileResponse = client_user.get_file(uploaded_image_url)
    assert file_response.status_code == status.HTTP_200_OK
    assert image_response.status_code == status.HTTP_200_OK

    parser = CncGen2MapParser(uploaded_file)
    assert parser.ini.get("CnCNet", "ID") == str(response.data["result"]["cnc_map_id"])

    map_object = CncMap.objects.get(id=response.data["result"]["cnc_map_id"])
    file_object = CncMapFile.objects.get(cnc_map_id=map_object.id)
    image_object = CncMapImageFile.objects.get(cnc_map_id=map_object.id)

    assert map_object
    assert file_object.cnc_user_id == client_user.kirovy_user.id
    assert image_object.cnc_user_id == client_user.kirovy_user.id
    assert map_object.cnc_user_id == client_user.kirovy_user.id
    assert file_object.ip_address == image_object.ip_address == "117.117.117.117"

    # Note: These won't match a md5 from the commandline because we add the ID to the map file.
    assert file_object.hash_md5 == file_utils.hash_file_md5(uploaded_file.open())
    file_map_desert.seek(0)
    assert file_object.hash_md5 != file_utils.hash_file_md5(file_map_desert.open())

    get_response = client_user.get(f"/maps/{map_object.id}/")

    assert get_response.status_code == status.HTTP_200_OK
    response_map = get_response.data["result"]

    # A lot of these will break if you change the desert.map file.
    assert response_map["cnc_user_id"] == str(client_user.kirovy_user.id)
    assert response_map["map_name"] == "desert", "Should match the name in the map file."
    assert response_map["cnc_game_id"] == str(game_uploadable.id)
    assert response_map["category_ids"] == [
        str(MapCategory.objects.get(name__iexact="standard").id),
    ]
    assert not response_map["is_published"], "Newly uploaded, unrefined, maps should default to unpublished."
    assert not response_map["is_temporary"], "Maps uploaded via a signed in user shouldn't be marked as temporary."
    assert not response_map["is_reviewed"], "Maps should not default to being reviewed."
    assert not response_map["is_banned"], "Happy path maps should not be banned on upload."
    assert response_map[
        "incomplete_upload"
    ], "Map files that have been uploaded via the UI should be marked as incomplete until the user sets map info."
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

    assert "ip_address" not in response_map.keys()


def test_map_file_upload_banned_user(file_map_desert, game_uploadable, client_banned):
    """Test that a banned user cannot upload a new map."""
    response = client_banned.post_file(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_uploadable.id)},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_map_file_upload_banned_map(banned_cheat_map, file_map_unfair, client_anonymous):
    """Test that an uploaded map will be rejected if the hash matches a banned one."""
    response = client_anonymous.post_file(
        _CLIENT_URL,
        {"file": file_map_unfair, "game": banned_cheat_map.cnc_game.slug},
        data_type=ui_objects.ErrorResponseData,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == UploadApiCodes.DUPLICATE_MAP
    assert response.data["additional"]["existing_map_id"] == str(banned_cheat_map.id)


def test_map_file_upload_game_allowances(
    client_user, client_moderator, file_map_desert, create_cnc_game, file_map_unfair
):
    """Test that we properly block uploads for invisible / restricted games for non-staff users."""
    visible_and_uploadable = create_cnc_game()
    invisible_and_uploadable = create_cnc_game("iu", is_visible=False, allow_public_uploads=True)
    visible_and_restricted = create_cnc_game("vr", is_visible=True, allow_public_uploads=False)

    user_expectations = {
        visible_and_uploadable: status.HTTP_201_CREATED,
        invisible_and_uploadable: status.HTTP_400_BAD_REQUEST,
        visible_and_restricted: status.HTTP_400_BAD_REQUEST,
    }

    for game, expectation in user_expectations.items():
        CncMap.objects.all().delete()
        file_map_desert.seek(0)
        response: KirovyResponse = client_user.post_file(
            _UPLOAD_URL,
            {"file": file_map_desert, "game_id": str(game.id)},
        )
        assert response.status_code == expectation, f"{game}, should have been {expectation}"
        assert expectation == status.HTTP_201_CREATED or response.data["message"] == "Game does not exist"

    for game, _ in user_expectations.items():
        CncMap.objects.all().delete()
        file_map_desert.seek(0)
        response: KirovyResponse = client_moderator.post_file(
            _UPLOAD_URL,
            # Need to use a different map to get passed the duplicate file checker.
            {"file": file_map_desert, "game_id": str(game.id)},
        )
        assert response.status_code == status.HTTP_201_CREATED


def test_map_file_upload__staff_ip(client_moderator, file_map_desert, game_uploadable, tmp_media_root):
    """Test uploading a map file via the UI endpoint has correct IP."""
    response = client_moderator.post_file(
        _UPLOAD_URL,
        {"file": file_map_desert, "game_id": str(game_uploadable.id)},
        HTTP_X_FORWARDED_FOR="117.117.117.117",
    )

    assert response.status_code == status.HTTP_201_CREATED

    map_id: str = response.data["result"]["cnc_map_id"]
    get_response: KirovyResponse[ResultResponseData] = client_moderator.get(f"/maps/{map_id}/")

    assert len(get_response.data["result"]["files"]) == 1
    assert (
        get_response.data["result"]["files"][0]["ip_address"]
        == CncMapFile.objects.get(cnc_map_id=map_id).ip_address
        == "staff"
    )
