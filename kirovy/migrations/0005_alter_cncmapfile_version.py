# Generated by Django 4.2.11 on 2024-05-14 06:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kirovy", "0004_cncmap_incomplete_upload"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cncmapfile",
            name="version",
            field=models.IntegerField(editable=False),
        ),
    ]