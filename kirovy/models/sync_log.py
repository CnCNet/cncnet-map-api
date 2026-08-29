import uuid

from django.db import models

from kirovy.models.cnc_game import CncGame


class SyncLog(models.Model):
    """A sync error log uploaded from a CnCNet game client.

    When a multiplayer game desyncs, the game engine writes SYNC{n}.TXT files (one per player slot).
    Clients upload these so admins can compare logs across machines to diagnose the desync.

    All clients in the same game session share the same ``game_hash`` (derived from the random seed
    and map SHA1), making it easy to group and compare logs from different players.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    game_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text='SHA1 of "{mapSha1}|{randomSeed}|{gameSlug}" as a lowercase hex string. Same for all players in the same game session.',
    )
    player_name = models.CharField(max_length=64)
    sync_file_index = models.SmallIntegerField(
        help_text="Player slot index from the SYNC filename (0-7). e.g. SYNC2.TXT → index 2.",
    )

    map_sha1 = models.CharField(max_length=40, blank=True)
    map_name = models.CharField(max_length=255, blank=True)
    game_mode = models.CharField(max_length=128, blank=True)
    cnc_game = models.ForeignKey(
        CncGame,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_logs",
    )

    file = models.FileField(upload_to="sync_logs/%Y/%m/%d/")
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes. Used for storage cap enforcement without filesystem calls.",
    )
    ip_address = models.GenericIPAddressField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "kirovy"
        indexes = [
            models.Index(fields=["game_hash", "sync_file_index"]),
            models.Index(fields=["uploaded_at"]),
        ]
        # One sync file per player slot per machine per game session.
        constraints = [
            models.UniqueConstraint(
                fields=["game_hash", "sync_file_index", "ip_address"],
                name="unique_sync_log_per_slot_per_machine",
            )
        ]

    def __str__(self):
        return f"SyncLog[{self.player_name} SYNC{self.sync_file_index} {self.game_hash[:8]}]"
