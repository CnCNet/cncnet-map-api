# Generated by Django 4.2.5 on 2023-10-22 05:35

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CncUser",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "cnc_net_id",
                    models.IntegerField(
                        editable=False,
                        help_text="The user ID from the CNCNet ladder API.",
                        unique=True,
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        help_text="The name from the CNCNet ladder API.", null=True
                    ),
                ),
                ("verified_map_uploader", models.BooleanField(default=False)),
                ("verified_email", models.BooleanField(default=False)),
                (
                    "group",
                    models.CharField(
                        help_text="The user group from the CNCNet ladder API."
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="CncGame",
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
                ("slug", models.CharField(max_length=16, unique=True)),
                ("full_name", models.CharField(max_length=128)),
                ("is_visible", models.BooleanField(default=False)),
                ("allow_public_uploads", models.BooleanField(default=False)),
                ("compatible_with_parent_maps", models.BooleanField(default=False)),
                ("is_mod", models.BooleanField(default=False)),
                (
                    "parent_game",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="kirovy.cncgame",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="CncMap",
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
                ("map_name", models.CharField(max_length=128)),
                ("description", models.CharField(max_length=4096)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="MapCategory",
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
                ("name", models.CharField(max_length=120)),
                ("slug", models.CharField(max_length=16)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="CncMapFile",
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
                ("name", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="")),
                ("file_extension", models.CharField(max_length=64)),
                ("hash_md5", models.CharField(max_length=32)),
                ("hash_sha512", models.CharField(max_length=512)),
                ("width", models.IntegerField()),
                ("height", models.IntegerField()),
                (
                    "cnc_map",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="kirovy.cncmap"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="cncmap",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="kirovy.mapcategory"
            ),
        ),
        migrations.AddField(
            model_name="cncmap",
            name="cnc_game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="kirovy.cncgame"
            ),
        ),
    ]