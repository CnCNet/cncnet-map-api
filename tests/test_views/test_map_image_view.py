import pathlib

import pytest
from PIL import Image, ExifTags

from kirovy.constants import api_codes
from kirovy.constants.api_codes import FileUploadApiCodes
from kirovy.models.cnc_map import CncMapImageFile
from kirovy.views.map_image_views import MapImageFileUploadView
from rest_framework import status


def test_map_image_upload__happy_path(create_cnc_map, file_map_image, client_user, get_file_path_for_uploaded_file_url):
    """Test that we can upload an image as a verified user, who has created a map.

    The PNG file should be converted to jpeg.
    """
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id, is_legacy=False, is_published=True, is_temporary=False)
    original_image_count = cnc_map.cncmapimagefile_set.select_related().count()
    response = client_user.post(
        "/maps/img/",
        {"file": file_map_image, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["message"] == MapImageFileUploadView.success_message
    saved_file = CncMapImageFile.objects.get(id=response.data["result"]["file_id"])
    image_url: str = response.data["result"]["file_url"]
    parent_id: str = response.data["result"]["parent_object_id"]

    assert parent_id == cnc_map.id
    expected_date = saved_file.created.date().isoformat()
    assert image_url == f"/silo/yr/map_images/{cnc_map.id.hex}/{expected_date}_{saved_file.id.hex}.jpg"

    assert get_file_path_for_uploaded_file_url(image_url).exists()

    assert cnc_map.cncmapimagefile_set.select_related().count() == original_image_count + 1
    # Image order starts at 0, then gets incremented, so image_order should be current_count - 1
    assert saved_file.image_order == original_image_count
    assert saved_file.name == pathlib.Path(file_map_image.name).stem + ".jpg"
    assert saved_file.file_extension.extension == "jpg"
    # Width and height are from the image itself.
    assert saved_file.width == 768
    assert saved_file.height == 494
    assert saved_file.cnc_user_id == client_user.kirovy_user.id
    assert saved_file.file.size < file_map_image.size, "Converting to jpeg should have shrunk the file size."

    # Check that the image gets returned with the map.
    get_response = client_user.get(f"/maps/{cnc_map.id}/")
    assert get_response.status_code == status.HTTP_200_OK

    map_images = get_response.data["result"]["images"]
    assert len(map_images) == 1
    assert map_images[0]["id"] == str(saved_file.id)


def test_map_image_upload__jpg(create_cnc_map, file_map_image_jpg, client_user, get_file_path_for_uploaded_file_url):
    """Test that we can upload a jpg.

    Image should be stripped of exif data.
    """
    with Image.open(file_map_image_jpg, "r") as raw_image:
        exif_data = raw_image.getexif()
        assert exif_data[ExifTags.Base.XPAuthor], "metadata for test image should exist."
    file_map_image_jpg.seek(0)
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id, is_legacy=False, is_published=True, is_temporary=False)
    response = client_user.post(
        "/maps/img/",
        {"file": file_map_image_jpg, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["message"] == MapImageFileUploadView.success_message
    saved_file = CncMapImageFile.objects.get(id=response.data["result"]["file_id"])
    assert saved_file.name == pathlib.Path(file_map_image_jpg.name).name
    assert saved_file.file_extension.extension == "jpg"

    # Width and height are from the image itself.
    assert saved_file.width == 993
    assert saved_file.height == 740
    assert saved_file.file.size < file_map_image_jpg.size

    with Image.open(saved_file.file) as processed_image:
        # exif data should have been removed.
        assert processed_image.getexif().get(ExifTags.Base.XPAuthor) is None
        assert not processed_image.getexif().keys()


@pytest.mark.parametrize("map_kwargs", [{"is_legacy": True}, {"is_temporary": True}])
def test_map_image_upload__unsupported_map(create_cnc_map, file_map_image, client_user, map_kwargs):
    """Test that map image uploads fail for legacy and temporary maps."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id, **map_kwargs)
    original_image_count = cnc_map.cncmapimagefile_set.select_related().count()
    response = client_user.post(
        "/maps/img/",
        {"file": file_map_image, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "Map type does not support custom preview images"
    assert response.data["code"] == FileUploadApiCodes.UNSUPPORTED

    assert cnc_map.cncmapimagefile_set.select_related().count() == original_image_count


def test_map_image_upload__user_is_banned(create_cnc_map, file_map_image, client_banned):
    """Test that map image uploads fail for banned users."""
    cnc_map = create_cnc_map(user_id=client_banned.kirovy_user.id)
    original_image_count = cnc_map.cncmapimagefile_set.select_related().count()
    response = client_banned.post(
        "/maps/img/",
        {"file": file_map_image, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert cnc_map.cncmapimagefile_set.select_related().count() == original_image_count


def test_map_image_upload__map_is_banned(create_cnc_map, file_map_image, client_user):
    """Test that map image uploads fail for banned maps."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id, is_banned=True)
    original_image_count = cnc_map.cncmapimagefile_set.select_related().count()
    response = client_user.post(
        "/maps/img/",
        {"file": file_map_image, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert cnc_map.cncmapimagefile_set.select_related().count() == original_image_count


def test_map_image_upload__not_an_image(create_cnc_map, file_map_desert, client_user):
    """Test that map image uploads fail for non-image files."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)
    original_image_count = cnc_map.cncmapimagefile_set.select_related().count()
    response = client_user.post(
        "/maps/img/",
        {"file": file_map_desert, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == FileUploadApiCodes.INVALID
    assert cnc_map.cncmapimagefile_set.select_related().count() == original_image_count


def test_map_image_upload__too_large(create_cnc_map, file_binary, client_user):
    """Test that map image uploads fail for files that are too large.

    This test works because the file size check happens before the extension check
    """
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)
    original_image_count = cnc_map.cncmapimagefile_set.select_related().count()
    response = client_user.post(
        "/maps/img/",
        {"file": file_binary, "cnc_map_id": str(cnc_map.id)},
        format="multipart",
        content_type=None,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == FileUploadApiCodes.TOO_LARGE
    assert cnc_map.cncmapimagefile_set.select_related().count() == original_image_count


def test_map_image_edit__happy_path(client_user, create_cnc_map, create_cnc_map_image_file, file_map_image):
    """Test that users can edit the editable fields on a map image."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)
    image_file = create_cnc_map_image_file(file_map_image, cnc_map)

    edit_values = {"image_order": 117, "name": "Tiberium Field Photo"}
    original_values = {key: getattr(image_file, key) for key in edit_values.keys()}
    for key, edit_value in edit_values.items():
        assert original_values[key] != edit_value

    # Make the edit request.
    response = client_user.patch(f"/maps/img/{image_file.id}/", data=edit_values)

    assert response.status_code == status.HTTP_200_OK
    image_file.refresh_from_db()

    assert image_file.image_order == 117
    assert image_file.name == "Tiberium Field Photo"


def test_map_image_edit__user_banned(ban_user, client_user, create_cnc_map, create_cnc_map_image_file, file_map_image):
    """Test that an error is raised if a banned user tries to edit an image."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)
    image_file = create_cnc_map_image_file(file_map_image, cnc_map)
    ban_user(user_to_ban=client_user.kirovy_user, ban_reason="GDI propaganda")

    edit_values = {"image_order": 117, "name": "Tiberium Field Photo"}

    # Make the edit request.
    response = client_user.patch(f"/maps/img/{image_file.id}/", data=edit_values)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    image_file.refresh_from_db()

    assert image_file.image_order != 117
    assert image_file.name != "Tiberium Field Photo"


def test_map_image_edit__uneditable_fields(client_user, create_cnc_map, create_cnc_map_image_file, file_map_image):
    """Test that an error is raised if a user tries to edit uneditable fields."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)
    other_map = create_cnc_map()
    image_file = create_cnc_map_image_file(file_map_image, cnc_map)

    edit_values = {"width": 90, "height": 90, "cnc_map_id": str(other_map.id)}

    # Make the edit request.
    response = client_user.patch(f"/maps/img/{image_file.id}/", data=edit_values)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "Requested fields cannot be edited after creation"
    assert response.data["code"] == api_codes.GenericApiCodes.CANNOT_UPDATE_FIELD
    assert set(response.data["additional"]["attempted"]) == {"width", "height", "cnc_map"}
    assert set(response.data["additional"]["can_update"]) == {"name", "image_order"}
