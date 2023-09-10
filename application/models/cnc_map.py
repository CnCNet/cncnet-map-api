import os.path

from django.conf import settings
from django.db import models

from application import constants
from application.models import file_base
from application.models import cnc_game


def get_map_upload_path(instance: "CncMapFile", filename: str) -> str:
    _, file_extension = os.path.splitext(filename)
    return os.path.join(
        settings.MEDIA_ROOT,
        constants.cnc_map_directory,
        instance.cnc_map.cnc_game.slug,
        instance.cnc_map.category.slug,
        instance.hash_md5,
        file_extension,
    )


class MapCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.CharField(max_length=16)


class CncMap(models.Model):
    """The Logical representation of a map for a Command & Conquer game.

    We have this as a separate model from the file model because later C&C's allow for various files
    like map previews, INI files, and string files, so this model will serve as a way to relate them all on the backend.
    """

    map_name = models.CharField(max_length=128)
    description = models.CharField(max_length=4096)
    cnc_game = models.ForeignKey(cnc_game.CncGame, models.PROTECT, null=False)
    category = models.ForeignKey(MapCategory, models.PROTECT, null=False)


class CncMapFile(file_base.CncNetFileBaseModel):
    """Represents the actual map file that a Command & Conquer game reads."""

    UPLOAD_TO = get_map_upload_path
    ALLOWED_EXTENSIONS = ["map", "yrm", "mpr", "mmx"]

    width = models.IntegerField()
    height = models.IntegerField()

    cnc_map = models.OneToOneField(CncMap, on_delete=models.CASCADE, null=False)
