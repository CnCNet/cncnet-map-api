import pathlib

from django.conf import settings
from django.db import models

from kirovy import exceptions
from kirovy.models import file_base
from kirovy.models import cnc_game as game_models, cnc_user
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy import typing as t


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
    cnc_game = models.ForeignKey(game_models.CncGame, models.PROTECT, null=False)
    category = models.ForeignKey(MapCategory, models.PROTECT, null=False)
    cncnet_user = models.ForeignKey(
        cnc_user.CncUser, on_delete=models.CASCADE, null=True
    )

    def next_version_number(self) -> int:
        """Generate the next version to use for a map file.

        :return:
            The current latest version, plus one.
        """
        previous_version: CncMapFile = (
            CncMapFile.objects.filter(cnc_map_id=self.id)
            .order_by("-version")
            .only("version")
            .first()
        )
        if not previous_version:
            return 1
        return previous_version.version + 1

    def get_map_directory_path(self) -> pathlib.Path:
        """Returns the path to the directory where all files related to the map will be store.

        :return:
            Directory path to put maps and image previews in.
        """
        return pathlib.Path(
            self.cnc_game.slug,
            settings.CNC_MAP_DIRECTORY,
            self.category.slug,
            str(self.id),
        )


class CncMapFile(file_base.CncNetFileBaseModel):
    """Represents the actual map file that a Command & Conquer game reads."""

    width = models.IntegerField()
    height = models.IntegerField()
    version = models.IntegerField()

    cnc_map = models.ForeignKey(CncMap, on_delete=models.CASCADE, null=False)

    ALLOWED_EXTENSION_TYPES = {game_models.CncFileExtension.ExtensionTypes.MAP.value}

    UPLOAD_TYPE = settings.CNC_MAP_DIRECTORY

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cnc_map_id", "version"], name="unique_map_version"
            ),
        ]

    def save(self, *args, **kwargs):
        self.version = self.cnc_map.next_version_number()
        super().save(*args, **kwargs)

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

    @staticmethod
    def generate_upload_to(instance: "CncMapFile", filename: str) -> pathlib.Path:
        filename = pathlib.Path(filename)
        final_file_name = f"{filename.stem}_v{instance.version}{filename.suffix}"

        # e.g. "yr/maps/battle/CNC_NET_MAP_ID/streets_of_gold_v1.map
        return pathlib.Path(instance.cnc_map.get_map_directory_path(), final_file_name)
