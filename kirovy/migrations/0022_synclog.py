import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kirovy", "0021_remove_cncmapfile_kirovy_cncm_cnc_map_a1e8af_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "game_hash",
                    models.CharField(
                        db_index=True,
                        help_text="SHA1 of (seed + map_sha1 + game_slug). Same for all players in the same game session.",
                        max_length=64,
                    ),
                ),
                ("player_name", models.CharField(max_length=64)),
                (
                    "sync_file_index",
                    models.SmallIntegerField(
                        help_text="Player slot index from the SYNC filename (0-7). e.g. SYNC2.TXT → index 2."
                    ),
                ),
                ("map_sha1", models.CharField(blank=True, max_length=40)),
                ("map_name", models.CharField(blank=True, max_length=255)),
                ("game_mode", models.CharField(blank=True, max_length=128)),
                (
                    "cnc_game",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sync_logs",
                        to="kirovy.cncgame",
                    ),
                ),
                ("file", models.FileField(upload_to="sync_logs/%Y/%m/%d/")),
                ("ip_address", models.GenericIPAddressField()),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "app_label": "kirovy",
            },
        ),
        migrations.AddIndex(
            model_name="synclog",
            index=models.Index(fields=["game_hash", "sync_file_index"], name="kirovy_sync_game_ha_idx"),
        ),
        migrations.AddIndex(
            model_name="synclog",
            index=models.Index(fields=["uploaded_at"], name="kirovy_sync_uploade_idx"),
        ),
        migrations.AddConstraint(
            model_name="synclog",
            constraint=models.UniqueConstraint(
                fields=["game_hash", "sync_file_index", "ip_address"],
                name="unique_sync_log_per_slot_per_machine",
            ),
        ),
    ]
