from rest_framework import status

from kirovy.models import MapCategory
from kirovy import typing as t

CATEGORY_URL = "/maps/categories/"


def test_map_category_create(kirovy_client, client_admin, client_moderator, client_user):
    """Test that admins can create map categories."""
    data = {
        "name": "Unholy Alliance, Taylor's Version",
    }
    # sliced to 16 characters, this would be "unholy-alliance-", but we should remove trailing hyphens.
    expected_slug = "unholy-alliance"

    # Make sure users below an admin cannot make categories.
    # If you change the permissions then you'll need to update this list.
    for client in [client_user, client_moderator, kirovy_client]:
        denied_response = client.post(CATEGORY_URL, data)
        assert denied_response.status_code == status.HTTP_403_FORBIDDEN

    response = client_admin.post(CATEGORY_URL, data)
    assert response.status_code == status.HTTP_201_CREATED
    post_data: dict = response.data

    map_category = MapCategory.objects.get(id=post_data["result"]["id"])
    assert map_category.name == data["name"]
    assert map_category.slug == expected_slug

    assert post_data["result"]["slug"] == expected_slug


def test_get_map_categories(client_user, create_cnc_map_category):
    expected_fields = {"name", "slug", "id", "modified", "created"}
    categories: t.Dict[str, MapCategory] = {str(c.id): c for c in MapCategory.objects.all()}
    for category_name in ["Slayer", "Team Slayer", "CTF", "Forge"]:
        category = create_cnc_map_category(category_name)
        categories[str(category.id)] = category

    response = client_user.get(CATEGORY_URL)

    assert response.status_code == status.HTTP_200_OK
    results: t.List[t.DictStrAny] = response.data.get("results")

    assert len(results) == len(categories)

    for result in results:
        assert set(result.keys()) == expected_fields, f"We should only read the fields: {expected_fields}"
        category = categories.get(result["id"])
        assert result["name"] == category.name
        assert result["slug"] == category.slug
