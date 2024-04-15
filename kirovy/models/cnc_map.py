import pathlib

from django.conf import settings
from django.db import models
from django.utils import text as text_utils

from kirovy.models import file_base
from kirovy.models import cnc_game as game_models, cnc_user
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy import typing as t


class MapCategory(CncNetBaseModel):
    name = models.CharField(max_length=120)
    slug = models.CharField(max_length=16)

    def set_slug_from_name(
        self, update_fields: t.Optional[t.List[str]] = None
    ) -> t.Optional[t.List[str]]:
        """Sets ``self.slug`` based on ``self.name``.

        :param update_fields:
            The ``update_fields`` from the ``.save`` call.
        :return:
            The ``update_fields`` for ``.save()``.
        """
        new_slug: str = text_utils.slugify(self.name, allow_unicode=False)[:16]
        new_slug = new_slug.rstrip(
            "-"
        )  # Remove trailing hyphens if the 16th character was unlucky.
        if new_slug != self.slug:
            self.slug = new_slug
            if update_fields and "slug" not in update_fields:
                update_fields.append("slug")

        return update_fields

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: t.Optional[str] = None,
        update_fields: t.Optional[t.List[str]] = None,
    ):
        update_fields = self.set_slug_from_name(update_fields)
        super().save(force_insert, force_update, using, update_fields)


class CncMap(cnc_user.CncNetUserOwnedModel):
    """The Logical representation of a map for a Command & Conquer game.

    We have this as a separate model from the file model because later C&C's allow for various files
    like map previews, INI files, and string files, so this model will serve as a way to relate them all on the backend.

    :attr:`~kirovy.models.cnc_map.CncMap.id` will be assigned to ``[CncNetId]`` in the map file.

    Gets ``cnc_user`` from :class:`~kirovy.models.cnc_user.CncNetUserOwnedModel`.
    """

    map_name = models.CharField(max_length=128, null=False)
    description = models.CharField(max_length=4096, null=False)
    cnc_game = models.ForeignKey(game_models.CncGame, models.PROTECT, null=False)
    categories = models.ManyToManyField(MapCategory)
    is_legacy = models.BooleanField(
        default=False,
        help_text="If true, this is an upload from the old cncnet database.",
    )
    """:attr:
        This will be set for all maps that we bulk upload from the legacy cncnet map database.
        It will never be set via the UI by regular users. Exceptions can be made if we find pld maps from the '00s.
    """

    legacy_upload_date = models.DateTimeField(
        default=None,
        null=True,
        help_text="The original upload date for entries imported from the legacy map database.",
    )
    """:attr: Tracks the original upload dates for legacy maps, for historical reasons."""

    is_published = models.BooleanField(
        default=False,
        help_text="If true, this map will show up in normal searches and feeds.",
    )
    """:attr:
        Did the map maker set this map to be published? Published maps show up in normal search and feeds.
        Maps will always be available via direct link, and users will be able to request non-published maps in searches.
    """

    is_temporary = models.BooleanField(
        default=False,
        help_text="If true, this will be deleted eventually. "
        "This flag is to support sharing in multiplayer lobbies.",
    )
    """:attr:
        Whether this map is temporary. We don't want to keep storing every map that is shared in a multiplayer lobby,
        so this flag will be set when a map is uploaded via the multiplayer lobby. It will not show up in feeds
        or searches. Won't have an owner until the client supports logging in.
    """

    is_reviewed = models.BooleanField(
        default=False, help_text="If true, this map was reviewed by a staff member."
    )

    is_banned = models.BooleanField(
        default=False,
        help_text="If true, this map will be hidden everywhere. Likely due to breaking a rule.",
    )
    """:attr: Keep banned maps around so we can keep track of rule-breakers."""

    incomplete_upload = models.BooleanField(
        default=False,
        help_text="If true, then the map file has been uploaded, but the map info has not been set yet.",
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
        """Generate the path to upload map files to.

        :param instance:
        :param filename:
            The filename of the uploaded file.
        :return:
            Path to upload map to relative to :attr:`~kirovy.settings.base.MEDIA_ROOT`.
        """
        filename = pathlib.Path(filename)
        final_file_name = f"{filename.stem}_v{instance.version}{filename.suffix}"

        # e.g. "yr/maps/CNC_NET_MAP_ID/streets_of_gold_v1.map
        return pathlib.Path(instance.cnc_map.get_map_directory_path(), final_file_name)
