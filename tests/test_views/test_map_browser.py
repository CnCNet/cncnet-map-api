"""Tests for the map browser's sorting and filtering on ``/maps/search/``."""

import datetime
from urllib.parse import urlencode

import pytest
from django.utils import timezone
from rest_framework import status

from kirovy.models import CncMap
from kirovy.objects.ui_objects import ListResponseData
from kirovy.response import KirovyResponse

BASE_URL = "/maps/search/"


def _search(client, **params) -> KirovyResponse[ListResponseData]:
    query = urlencode(params, doseq=True)
    response: KirovyResponse[ListResponseData] = client.get(f"{BASE_URL}?{query}")
    assert response.status_code == status.HTTP_200_OK, response.data
    return response


def _result_ids(response: KirovyResponse[ListResponseData]) -> list[str]:
    return [result["id"] for result in response.data["results"]]


def _record_downloads(cnc_map: CncMap, count: int, days_ago: int = 0) -> None:
    download_date = timezone.now().date() - datetime.timedelta(days=days_ago)
    for _ in range(count):
        cnc_map.record_download(download_date)


def _set_created(cnc_map: CncMap, days_ago: int) -> None:
    CncMap.objects.filter(id=cnc_map.id).update(created=timezone.now() - datetime.timedelta(days=days_ago))


def test_search_ordering__popular(create_cnc_map, client_anonymous):
    """``popular`` sorts by all-time downloads, regardless of when they happened."""
    unpopular = create_cnc_map("Unpopular")
    old_favorite = create_cnc_map("Old Favorite")
    new_hotness = create_cnc_map("New Hotness")
    _record_downloads(old_favorite, 5, days_ago=60)
    _record_downloads(new_hotness, 3)

    response = _search(client_anonymous, ordering="popular")

    assert _result_ids(response) == [str(old_favorite.id), str(new_hotness.id), str(unpopular.id)]
    assert response.data["results"][0]["download_count"] == 5


def test_search_ordering__trending(create_cnc_map, client_anonymous, settings):
    """``trending`` only counts downloads inside the trending window."""
    settings.MAP_TRENDING_WINDOW_DAYS = 7
    old_favorite = create_cnc_map("Old Favorite")
    new_hotness = create_cnc_map("New Hotness")
    edge_of_window = create_cnc_map("Edge Of Window")
    _record_downloads(old_favorite, 10, days_ago=8)  # Just outside the window.
    _record_downloads(old_favorite, 1, days_ago=0)
    _record_downloads(new_hotness, 3, days_ago=1)
    _record_downloads(edge_of_window, 2, days_ago=6)  # Last day inside the window.

    response = _search(client_anonymous, ordering="trending")

    assert _result_ids(response) == [str(new_hotness.id), str(edge_of_window.id), str(old_favorite.id)]


def test_search_ordering__newest_is_default(create_cnc_map, client_anonymous):
    oldest = create_cnc_map("Oldest")
    newest = create_cnc_map("Newest")
    middle = create_cnc_map("Middle")
    _set_created(oldest, 30)
    _set_created(middle, 10)
    _set_created(newest, 1)

    expected = [str(newest.id), str(middle.id), str(oldest.id)]
    assert _result_ids(_search(client_anonymous)) == expected
    assert _result_ids(_search(client_anonymous, ordering="newest")) == expected
    assert _result_ids(_search(client_anonymous, ordering="created")) == list(reversed(expected))


def test_search_ordering__updated(
    create_cnc_map, create_cnc_map_file, client_anonymous, file_map_desert, file_map_valid
):
    """``updated`` sorts by the newest uploaded file version, not by when the map was created."""
    updated_recently = create_cnc_map("Updated Recently", file=file_map_desert)
    created_recently = create_cnc_map("Created Recently", file=file_map_valid)
    _set_created(updated_recently, 30)
    # Upload a new version of the older map, after the newer map's only version.
    file_map_valid.seek(0)
    create_cnc_map_file(file_map_valid, updated_recently)

    response = _search(client_anonymous, ordering="updated")

    assert _result_ids(response) == [str(updated_recently.id), str(created_recently.id)]


def test_search_ordering__map_name_and_size(
    create_cnc_map, client_anonymous, file_map_desert, file_map_valid, file_map_unfair
):
    desert = create_cnc_map("Bravo Desert", file=file_map_desert)  # 116 x 62
    valid = create_cnc_map("Alpha Valid", file=file_map_valid)  # 73 x 69
    unfair = create_cnc_map("Charlie Unfair", file=file_map_unfair)  # 75 x 74

    assert _result_ids(_search(client_anonymous, ordering="map_name")) == [
        str(valid.id),
        str(desert.id),
        str(unfair.id),
    ]
    assert _result_ids(_search(client_anonymous, ordering="-latest_file_width")) == [
        str(desert.id),
        str(unfair.id),
        str(valid.id),
    ]
    assert _result_ids(_search(client_anonymous, ordering="latest_file_height")) == [
        str(desert.id),
        str(valid.id),
        str(unfair.id),
    ]


@pytest.mark.parametrize("ordering", ["cnc_map_file__width", "ip_address", "-popular", "is_banned"])
def test_search_ordering__invalid_fields_fall_back_to_default(create_cnc_map, client_anonymous, ordering):
    """Unknown or non-whitelisted ordering fields are ignored instead of causing a server error."""
    older = create_cnc_map("Older")
    newer = create_cnc_map("Newer")
    _set_created(older, 5)

    response = _search(client_anonymous, ordering=ordering)

    assert _result_ids(response) == [str(newer.id), str(older.id)]


def test_search_filter__author(create_cnc_map, create_kirovy_user, client_anonymous):
    kane = create_kirovy_user(username="Kane")
    seth = create_kirovy_user(username="Seth")
    kane_map = create_cnc_map("Temple Prime", user_id=kane.id)
    create_cnc_map("Seth's Hideout", user_id=seth.id)

    by_name = _search(client_anonymous, author="kane")
    by_id = _search(client_anonymous, cnc_user_id=str(kane.id))

    assert _result_ids(by_name) == [str(kane_map.id)]
    assert by_name.data["results"][0]["cnc_user_name"] == "Kane"
    assert _result_ids(by_id) == [str(kane_map.id)]


def test_search_filter__category_slug(create_cnc_map, create_cnc_map_category, client_anonymous):
    standard = create_cnc_map_category("Standard")
    koth = create_cnc_map_category("King of the Hill")
    naval = create_cnc_map_category("Naval")
    standard_map = create_cnc_map("Standard Map", map_categories=[standard])
    both_map = create_cnc_map("Both Map", map_categories=[standard, koth])
    create_cnc_map("Naval Map", map_categories=[naval])

    response = _search(client_anonymous, category_slug=[standard.slug, koth.slug])

    assert sorted(_result_ids(response)) == sorted([str(standard_map.id), str(both_map.id)])


def test_search_filter__size_uses_latest_version(
    create_cnc_map, create_cnc_map_file, client_anonymous, file_map_desert, file_map_valid, file_map_unfair
):
    """Size filters check the newest map file, so a map that shrank in v2 isn't returned as "large"."""
    large = create_cnc_map("Large", file=file_map_desert)  # 116 x 62
    shrunk = create_cnc_map("Shrunk", file=file_map_unfair)  # v1: 75 x 74
    create_cnc_map_file(file_map_valid, shrunk)  # v2: 73 x 69
    create_cnc_map("No File")  # Size unknown, excluded by any size filter.

    assert _result_ids(_search(client_anonymous, min_width=100)) == [str(large.id)]
    assert _result_ids(_search(client_anonymous, max_width=80)) == [str(shrunk.id)]
    assert _result_ids(_search(client_anonymous, min_height=70)) == []
    assert _result_ids(_search(client_anonymous, min_height=60, max_height=65)) == [str(large.id)]


def test_search_filter__created_range(create_cnc_map, client_anonymous):
    old_map = create_cnc_map("Old Map")
    new_map = create_cnc_map("New Map")
    _set_created(old_map, 40)
    cutoff = (timezone.now() - datetime.timedelta(days=20)).isoformat()

    assert _result_ids(_search(client_anonymous, created_after=cutoff)) == [str(new_map.id)]
    assert _result_ids(_search(client_anonymous, created_before=cutoff)) == [str(old_map.id)]


def test_search_filter__curated(create_cnc_map, client_anonymous):
    """Staff-reviewed maps can be listed on their own, e.g. for a curated map list."""
    curated = create_cnc_map("Curated", is_reviewed=True)
    create_cnc_map("Not Curated")

    assert _result_ids(_search(client_anonymous, is_reviewed=True)) == [str(curated.id)]


def test_search_combined_filters_and_trending_pagination(create_cnc_map, create_cnc_map_category, client_anonymous):
    """Filters, search, trending annotations, and pagination work together without duplicate rows."""
    standard = create_cnc_map_category("Standard")
    koth = create_cnc_map_category("King of the Hill")
    maps = [create_cnc_map(f"Arena {i}", map_categories=[standard, koth]) for i in range(5)]
    for downloads, cnc_map in enumerate(maps):
        _record_downloads(cnc_map, downloads)

    first_page = _search(
        client_anonymous, search="arena", category_slug=[standard.slug, koth.slug], ordering="trending", limit=2
    )
    second_page = _search(
        client_anonymous,
        search="arena",
        category_slug=[standard.slug, koth.slug],
        ordering="trending",
        limit=2,
        offset=2,
    )

    assert _result_ids(first_page) == [str(maps[4].id), str(maps[3].id)]
    assert _result_ids(second_page) == [str(maps[2].id), str(maps[1].id)]
    assert first_page.data["pagination_metadata"]["remaining_count"] == 5
