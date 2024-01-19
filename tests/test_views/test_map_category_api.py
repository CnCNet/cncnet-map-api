from rest_framework import status

from kirovy.models import MapCategory

CATEGORY_URL = "/map-categories/"


def test_map_category_create(
    kirovy_client, client_admin, client_moderator, client_user
):
    """Test that admins can create map categories."""
    data = {
        "name": "Unholy Alliance",
        "slug": "ra_uall",
    }

    # Make sure users below an admin cannot make categories.
    for client in [client_user, client_moderator, kirovy_client]:
        denied_response = client.post(CATEGORY_URL, data)
        assert denied_response.status_code == status.HTTP_403_FORBIDDEN

    response = client_admin.post(CATEGORY_URL, data)
    assert response.status_code == status.HTTP_201_CREATED
    post_data: dict = response.data

    map_category = MapCategory.objects.get(id=post_data["id"])
    assert map_category.name == data["name"]
    assert map_category.slug == data["slug"]
