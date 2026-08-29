from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kirovy", "0022_synclog"),
    ]

    operations = [
        migrations.AddField(
            model_name="synclog",
            name="file_size",
            field=models.PositiveIntegerField(
                default=0,
                help_text="File size in bytes. Used for storage cap enforcement without filesystem calls.",
            ),
        ),
    ]
