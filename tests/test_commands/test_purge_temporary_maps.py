"""Tests for ``manage.py purge_temporary_maps``."""

import datetime
import io

import pytest
from django.core.management import call_command, CommandError
from django.utils import timezone

from kirovy.models import CncMap, CncMapFile


def _age(cnc_map: CncMap, days: int) -> None:
    CncMap.objects.filter(id=cnc_map.id).update(created=timezone.now() - datetime.timedelta(days=days))


@pytest.fixture
def temporary_maps(create_cnc_map, file_map_desert, file_map_valid, file_map_unfair):
    """Temporary maps covering every purge rule. Only ``stale`` should be purged with ``--days 30``."""
    stale = create_cnc_map("Stale Lobby Map", is_temporary=True, is_published=False, file=file_map_desert)
    recent = create_cnc_map("Recent Lobby Map", is_temporary=True, is_published=False)
    still_played = create_cnc_map("Still Played", is_temporary=True, is_published=False, file=file_map_valid)
    banned = create_cnc_map("Banned Cheat Map", is_temporary=True, is_banned=True, file=file_map_unfair)
    has_edit = create_cnc_map("Edited By Someone", is_temporary=True, is_published=False)
    edit = create_cnc_map("The Edit")
    CncMap.objects.filter(id=edit.id).update(parent=has_edit)
    permanent = create_cnc_map("Account Upload", is_temporary=False)

    for old_map in [stale, still_played, banned, has_edit, permanent]:
        _age(old_map, 90)
    _age(recent, 5)
    still_played.record_download(timezone.now().date() - datetime.timedelta(days=2))

    return {
        "stale": stale,
        "recent": recent,
        "still_played": still_played,
        "banned": banned,
        "has_edit": has_edit,
        "permanent": permanent,
    }


def test_purge_temporary_maps__dry_run(temporary_maps):
    out = io.StringIO()

    call_command("purge_temporary_maps", "--days", "30", "--dry-run", stdout=out)

    assert "1 temporary maps would be purged." in out.getvalue()
    assert CncMap.objects.filter(id=temporary_maps["stale"].id).exists()


def test_purge_temporary_maps(temporary_maps, django_capture_on_commit_callbacks):
    stale = temporary_maps["stale"]
    stale_file: CncMapFile = stale.cncmapfile_set.get()
    storage, file_name = stale_file.file.storage, stale_file.file.name
    assert storage.exists(file_name)
    out = io.StringIO()

    with django_capture_on_commit_callbacks(execute=True):
        call_command("purge_temporary_maps", "--days", "30", stdout=out)

    assert "Purged 1 temporary maps." in out.getvalue()
    assert not CncMap.objects.filter(id=stale.id).exists()
    assert not CncMapFile.objects.filter(id=stale_file.id).exists()
    assert not storage.exists(file_name), "The map file should be removed from disk too."
    for kept in ["recent", "still_played", "banned", "has_edit", "permanent"]:
        assert CncMap.objects.filter(id=temporary_maps[kept].id).exists(), kept


def test_purge_temporary_maps__days_must_be_positive(db):
    with pytest.raises(CommandError):
        call_command("purge_temporary_maps", "--days", "0")
