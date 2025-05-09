# Generated by Django 4.2.11 on 2024-08-15 04:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import kirovy.models.file_base
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("kirovy", "0008_alter_cncfileextension_extension_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="MapPreview",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("modified", models.DateTimeField(auto_now=True, null=True)),
                ("name", models.CharField(max_length=255)),
                (
                    "file",
                    models.FileField(
                        upload_to=kirovy.models.file_base._generate_upload_to
                    ),
                ),
                ("hash_md5", models.CharField(max_length=32)),
                ("hash_sha512", models.CharField(max_length=512)),
                ("is_extracted", models.BooleanField()),
                (
                    "cnc_game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="kirovy.cncgame"
                    ),
                ),
                (
                    "cnc_map_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="kirovy.cncmapfile",
                    ),
                ),
                (
                    "file_extension",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="kirovy.cncfileextension",
                    ),
                ),
                (
                    "last_modified_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="modified_%(class)s_set",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
