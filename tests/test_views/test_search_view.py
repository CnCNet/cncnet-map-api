from urllib.parse import urlencode

from rest_framework import status

from kirovy.objects.ui_objects import ListResponseData
from kirovy.response import KirovyResponse

BASE_URL = "/maps/search/"


def test_search_map_name(create_cnc_map, client_anonymous):
    create_cnc_map("Streets of gold", is_published=True)
    expected = create_cnc_map("Silver Road", is_published=True)

    query = urlencode({"search": "silver"})

    response: KirovyResponse[ListResponseData] = client_anonymous.get(BASE_URL + "?" + query)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == str(expected.id)
    assert "ip_address" not in response.data["results"][0].keys()


def test_search_map__categories(create_cnc_map, client_anonymous, create_cnc_map_category):
    included_category_1 = create_cnc_map_category("Halo Gen")
    included_category_2 = create_cnc_map_category("Mental Omega Oil Rush")
    # Unincluded isn't grammatically correct, but "excluded" implies filtering this category out.
    # "Unincluded" is accurate because we're not specifically including it.
    unincluded_category = create_cnc_map_category("Turtler's Paradise")

    # Maps should be included if they have any of the queried categories.
    map_both_categories = create_cnc_map(map_categories=[included_category_1, included_category_2])
    map_one_category = create_cnc_map("Delta Halo", map_categories=[included_category_1])
    map_one_category_and_unincluded = create_cnc_map(map_categories=[included_category_1, unincluded_category])

    # Maps should not be included if they don't have any of the queried categories.
    map_unincluded = create_cnc_map(map_categories=[unincluded_category])

    expected_map_ids = {str(x.id) for x in [map_both_categories, map_one_category, map_one_category_and_unincluded]}
    query = urlencode([("categories", str(x.id)) for x in [included_category_1, included_category_2]])

    response: KirovyResponse[ListResponseData] = client_anonymous.get(f"{BASE_URL}?{query}")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 3

    result_ids = {x["id"] for x in response.data["results"]}

    assert result_ids == expected_map_ids
