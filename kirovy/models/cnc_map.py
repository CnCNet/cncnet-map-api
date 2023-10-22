import pathlib

from django.conf import settings
from django.db import models

from kirovy.models import file_base
from kirovy.models import cnc_game
from kirovy.models.cnc_base_model import CncNetBaseModel


class MapCategory(CncNetBaseModel):
    name = models.CharField(max_length=120)
    slug = models.CharField(max_length=16)


class CncMap(CncNetBaseModel):
    """The Logical representation of a map for a Command & Conquer game.

    We have this as a separate model from the file model because later C&C's allow for various files
    like map previews, INI files, and string files, so this model will serve as a way to relate them all on the backend.

    :attr:`~kirovy.models.cnc_map.CncMap.id` will be assigned to ``[CncNetId]`` in the map file.
    """

    map_name = models.CharField(max_length=128)
    description = models.CharField(max_length=4096)
    cnc_game = models.ForeignKey(cnc_game.CncGame, models.PROTECT, null=False)
    category = models.ForeignKey(MapCategory, models.PROTECT, null=False)

    def get_map_directory_path(self) -> pathlib.Path:
        """Returns the path to the directory where all files related to the map will be store.

        :return:
            Directory path to put maps and image previews in.
        """
        return pathlib.Path(
            settings.CNC_MAP_DIRECTORY,
            self.cnc_game.slug,
            self.category.slug,
            str(self.id),
        )


class CncMapFile(file_base.CncNetFileBaseModel):
    """Represents the actual map file that a Command & Conquer game reads."""

    ALLOWED_EXTENSIONS = ["map", "yrm", "mpr", "mmx"]

    width = models.IntegerField()
    height = models.IntegerField()

    cnc_map = models.OneToOneField(CncMap, on_delete=models.CASCADE, null=False)

    def get_map_upload_path(self, filename: str) -> pathlib.Path:
        """Generate the upload path for the map file.

        :param filename:
            The filename that the user uploaded.
        :return:
            Path to store the map file in.
            This path is not guaranteed to exist because we use this function on first-save.
        """
        directory = self.cnc_map.get_map_directory_path()
        return pathlib.Path(directory, filename)
