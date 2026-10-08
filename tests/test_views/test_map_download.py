"""Tests for map downloads and download counting."""

import datetime
import hashlib

import pytest
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status

from kirovy.models import CncGame, CncMap
from kirovy.models.cnc_map import CncMapDownloadStat


def _download_url(cnc_map: CncMap) -> str:
    return f"/maps/{cnc_map.id}/download/"


def test_record_download__counts_total_and_per_day(cnc_map):
    today = timezone.now().date()
    yesterday = today - datetime.timedelta(days=1)

    cnc_map.record_download(yesterday)
    cnc_map.record_download(today)
    cnc_map.record_download(today)

    cnc_map.refresh_from_db()
    assert cnc_map.download_count == 3
    daily = dict(CncMapDownloadStat.objects.filter(cnc_map=cnc_map).values_list("date", "download_count"))
    assert daily == {yesterday: 1, today: 2}


def test_record_download__stale_instance_save_does_not_reset_count(cnc_map, client_user):
    """Editing a map must not overwrite the download counter with the stale value on the instance."""
    stale_instance = CncMap.objects.get(id=cnc_map.id)
    cnc_map.record_download()
    cnc_map.record_download()

    response = client_user.patch(f"/maps/{stale_instance.id}/", data={"description": "Edited after downloads."})

    assert response.status_code == status.HTTP_200_OK
    stale_instance.refresh_from_db()
    assert stale_instance.download_count == 2


def test_map_download__latest_version(
    create_cnc_map, create_cnc_map_file, client_anonymous, file_map_desert, file_map_valid
):
    cnc_map = create_cnc_map(file=file_map_desert)
    latest = create_cnc_map_file(file_map_valid, cnc_map)
    assert latest.version == 2

    response: FileResponse = client_anonymous.get(_download_url(cnc_map))

    assert response.status_code == status.HTTP_200_OK
    assert hashlib.sha1(response.getvalue()).hexdigest() == latest.hash_sha1
    assert latest.name in response.headers["Content-Disposition"]
    cnc_map.refresh_from_db()
    assert cnc_map.download_count == 1


def test_map_download__specific_version(
    create_cnc_map, create_cnc_map_file, client_anonymous, file_map_desert, file_map_valid
):
    cnc_map = create_cnc_map(file=file_map_desert)
    create_cnc_map_file(file_map_valid, cnc_map)
    first = cnc_map.cncmapfile_set.get(version=1)

    response: FileResponse = client_anonymous.get(_download_url(cnc_map) + "?version=1")

    assert response.status_code == status.HTTP_200_OK
    assert hashlib.sha1(response.getvalue()).hexdigest() == first.hash_sha1


@pytest.mark.parametrize("version", ["3", "abc", "-1"])
def test_map_download__missing_version(create_cnc_map, client_anonymous, file_map_desert, version):
    cnc_map = create_cnc_map(file=file_map_desert)

    response = client_anonymous.get(_download_url(cnc_map) + f"?version={version}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    cnc_map.refresh_from_db()
    assert cnc_map.download_count == 0


def test_map_download__no_files(create_cnc_map, client_anonymous):
    cnc_map = create_cnc_map()

    response = client_anonymous.get(_download_url(cnc_map))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_map_download__visibility(create_cnc_map, create_client, create_kirovy_user, client_moderator, file_map_desert):
    """Banned and unpublished maps can only be downloaded by their owner, or staff."""
    owner = create_kirovy_user(username="Owner")
    stranger_client = create_client(create_kirovy_user(username="Stranger"))
    owner_client = create_client(owner)
    banned = create_cnc_map("Banned", user_id=owner.id, is_banned=True, file=file_map_desert)
    file_map_desert.seek(0)

    assert stranger_client.get(_download_url(banned)).status_code == status.HTTP_404_NOT_FOUND
    assert owner_client.get(_download_url(banned)).status_code == status.HTTP_200_OK
    assert client_moderator.get(_download_url(banned)).status_code == status.HTTP_200_OK


def test_map_download__unpublished_hidden_from_anonymous(create_cnc_map, client_anonymous, file_map_desert):
    draft = create_cnc_map("Draft", is_published=False, file=file_map_desert)

    assert client_anonymous.get(_download_url(draft)).status_code == status.HTTP_404_NOT_FOUND


def test_map_download__backwards_compatible_counts_downloads(
    create_cnc_map, create_cnc_map_file, file_map_desert, client_anonymous
):
    """Downloads from legacy clients count toward popularity too."""
    game = CncGame.objects.get(slug__iexact="yr")
    cnc_map = create_cnc_map(is_temporary=True, cnc_game=game, is_mapdb1_compatible=True)
    map_file = create_cnc_map_file(file_map_desert, cnc_map, zip_for_legacy=True)

    response: FileResponse = client_anonymous.get(f"/yr/{map_file.hash_sha1}.zip")

    assert response.status_code == status.HTTP_200_OK
    cnc_map.refresh_from_db()
    assert cnc_map.download_count == 1
    assert CncMapDownloadStat.objects.get(cnc_map=cnc_map).download_count == 1


def test_map_download__backwards_compatible_banned_map(
    create_cnc_map, create_cnc_map_file, file_map_unfair, client_anonymous
):
    """Legacy clients must not be able to download a map after a moderator bans it."""
    game = CncGame.objects.get(slug__iexact="yr")
    cnc_map = create_cnc_map(is_temporary=True, cnc_game=game, is_mapdb1_compatible=True, is_banned=True)
    map_file = create_cnc_map_file(file_map_unfair, cnc_map, zip_for_legacy=True)

    response = client_anonymous.get(f"/yr/{map_file.hash_sha1}.zip")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    cnc_map.refresh_from_db()
    assert cnc_map.download_count == 0
