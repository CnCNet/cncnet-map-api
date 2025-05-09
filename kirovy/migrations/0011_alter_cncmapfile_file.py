# Generated by Django 4.2.20 on 2025-03-17 20:32

from django.db import migrations, models
import kirovy.models.file_base
import kirovy.zip_storage


class Migration(migrations.Migration):

    dependencies = [
        ("kirovy", "0010_cncmapfile_hash_sha1_mappreview_hash_sha1"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cncmapfile",
            name="file",
            field=models.FileField(
                storage=kirovy.zip_storage.ZipFileStorage, upload_to=kirovy.models.file_base._generate_upload_to
            ),
        ),
    ]
