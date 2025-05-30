# Generated by Django 4.2.11 on 2024-08-15 03:35

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

from kirovy import typing
from kirovy.models import CncFileExtension as _Ext, CncUser as _User


def _forward(apps: StateApps, schema_editor: DatabaseSchemaEditor):

    # This is necessary in case later migrations make schema changes to these models.
    # Importing them normally will use the latest schema state and will crash if those
    # migrations are after this one.
    CncFileExtension: typing.Type[_Ext] = apps.get_model("kirovy", "CncFileExtension")
    CncUser: typing.Type[_User] = apps.get_model("kirovy", "CncUser")

    migration_user = CncUser.objects.get_or_create_migration_user()

    jpg = CncFileExtension(
        extension="jpg",
        extension_type=_Ext.ExtensionTypes.IMAGE.value,
        about="Jpg files are used for previews on the website and in the client.",
        last_modified_by_id=migration_user.id,
    )
    jpg.save()

    jpeg = CncFileExtension(
        extension="jpeg",
        extension_type=_Ext.ExtensionTypes.IMAGE.value,
        about="Jpeg files are used for previews on the website and in the client.",
        last_modified_by_id=migration_user.id,
    )
    jpeg.save()

    png = CncFileExtension(
        extension="png",
        extension_type=_Ext.ExtensionTypes.IMAGE.value,
        about="PNG files are used for previews on the website and in the client.",
        last_modified_by_id=migration_user.id,
    )
    png.save()


def _backward(apps: StateApps, schema_editor: DatabaseSchemaEditor):
    """Deleting the games on accident could be devastating to the db so no."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kirovy", "0006_cncmap_parent"),
    ]

    operations = [
        migrations.RunPython(_forward, reverse_code=_backward, elidable=False),
    ]
