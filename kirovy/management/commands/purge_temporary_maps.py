"""Delete temporary maps that were shared through CnCNet client lobbies and are no longer being used.

Maps uploaded by the CnCNet client (anonymous lobby shares) are flagged with
:attr:`kirovy.models.cnc_map.CncMap.is_temporary`. MapDB 2.0 doesn't need to keep them forever;
map authors who want a permanent copy upload their map with a CnCNet account.

Usage::

    python manage.py purge_temporary_maps --days 90 --dry-run
    python manage.py purge_temporary_maps --days 90

A temporary map is purged when **all** of these are true:

- It was uploaded more than ``--days`` days ago.
- It hasn't been downloaded within the last ``--days`` days (so maps still being played survive).
- It isn't banned. Banned maps are kept so that their hashes keep blocking re-uploads.
- It isn't a legacy map, and no other map lists it as its parent (so edits keep their credit).
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from kirovy import logging
from kirovy.models import CncMap

_LOGGER = logging.get_logger(__name__)


def get_purgeable_temporary_maps(days: int, now: datetime.datetime | None = None) -> QuerySet[CncMap]:
    """Get the temporary maps that are old enough, and unused enough, to delete.

    :param days:
        Maps must be older than this, and not downloaded within this many days.
    :param now:
        Override the current time for tests.
    :return:
        The maps that can be purged.
    """
    now = now or timezone.now()
    cutoff = now - datetime.timedelta(days=days)
    child_maps = CncMap.objects.filter(parent_id=OuterRef("pk"))
    return (
        CncMap.objects.filter(is_temporary=True, is_legacy=False, is_banned=False, created__lt=cutoff)
        .exclude(download_stats__date__gte=cutoff.date())
        .exclude(Exists(child_maps))
    )


def purge_map(cnc_map: CncMap) -> None:
    """Delete a map, its files, and its images, including the files on disk."""
    with transaction.atomic():
        stored_files = [*cnc_map.cncmapfile_set.all(), *cnc_map.cncmapimagefile_set.all()]
        cnc_map.delete()
        # Only remove files from storage once the database rows are gone.
        transaction.on_commit(lambda: [f.file.delete(save=False) for f in stored_files if f.file])


class Command(BaseCommand):
    help = "Delete temporary (CnCNet client lobby) map uploads that are old and haven't been downloaded recently."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            required=True,
            help="Purge temporary maps uploaded more than this many days ago that weren't downloaded in this window.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print how many maps would be purged.",
        )

    def handle(self, *args, days: int, dry_run: bool, **options) -> None:
        if days < 1:
            raise CommandError("--days must be at least 1")

        purgeable = get_purgeable_temporary_maps(days)
        count = purgeable.count()
        if dry_run:
            self.stdout.write(f"{count} temporary maps would be purged.")
            return

        purged = 0
        # Grab the IDs up front so that we aren't deleting rows out from under an open cursor.
        for map_id in list(purgeable.values_list("id", flat=True)):
            cnc_map = CncMap.objects.filter(id=map_id).first()
            if cnc_map:
                purge_map(cnc_map)
                purged += 1

        _LOGGER.info("purged_temporary_maps", purged=purged, days=days)
        self.stdout.write(f"Purged {purged} temporary maps.")
