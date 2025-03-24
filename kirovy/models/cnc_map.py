import pathlib

from django.conf import settings
from django.db import models
from django.utils import text as text_utils

from kirovy.models import file_base
from kirovy.models import cnc_game as game_models, cnc_user
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy import typing as t, exceptions


class MapCategory(CncNetBaseModel):
    name = models.CharField(max_length=120)
    """The name of the map category. Should match the lowercase of strings from a map file's game modes section."""
    slug = models.CharField(max_length=16)
    """Unique slug for URLs, auto-generated from the :attr:`~kirovy.models.cnc_map.MapCategory.name`."""

    def _set_slug_from_name(self, update_fields: t.Optional[t.List[str]] = None) -> t.Optional[t.List[str]]:
        """Sets ``self.slug`` based on ``self.name``.

        :param update_fields:
            The ``update_fields`` from the ``.save`` call.
        :return:
            The ``update_fields`` for ``.save()``.
        """
        new_slug: str = text_utils.slugify(self.name, allow_unicode=False)[:16]
        new_slug = new_slug.rstrip("-")  # Remove trailing hyphens if the 16th character was unlucky.

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
        update_fields = self._set_slug_from_name(update_fields)
        super().save(force_insert, force_update, using, update_fields)


class CncMap(cnc_user.CncNetUserOwnedModel):
    """The Logical representation of a map for a Command & Conquer game.

    We have this as a separate model from the file model because later C&C's allow for various files
    like map previews, INI files, and string files, so this model will serve as a way to relate them all on the backend.

    :attr:`~kirovy.models.cnc_map.CncMap.id` will be assigned to ``[CncNetId]`` in the map file.

    Gets ``cnc_user`` from :class:`~kirovy.models.cnc_user.CncNetUserOwnedModel`.
    """

    map_name = models.CharField(max_length=128, null=False, blank=False)
    description = models.CharField(max_length=4096, null=False, blank=False)
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

    is_reviewed = models.BooleanField(default=False, help_text="If true, this map was reviewed by a staff member.")

    is_banned = models.BooleanField(
        default=False,
        help_text="If true, this map will be hidden everywhere. Likely due to breaking a rule.",
    )
    """:attr: Keep banned maps around so we can keep track of rule-breakers."""

    incomplete_upload = models.BooleanField(
        default=False,
        help_text="If true, then the map file has been uploaded, but the map info has not been set yet.",
    )

    cnc_game = models.ForeignKey(game_models.CncGame, models.PROTECT, null=False)
    categories = models.ManyToManyField(MapCategory)
    parent = models.ForeignKey(
        "CncMap",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    """If set, then this map is a child of ``parent``. Used to track edits of other peoples' maps."""

    is_mapdb1_compatible = models.BooleanField(default=False)
    """If true, then this map was uploaded by a legacy CnCNet client and is backwards compatible with map db 1.0.

    This should never be set for maps uploaded via the web UI.
    """

    def next_version_number(self) -> int:
        """Generate the next version to use for a map file.

        :return:
            The current latest version, plus one.
        """
        previous_version: CncMapFile = (
            CncMapFile.objects.filter(cnc_map_id=self.id).order_by("-version").only("version").first()
        )
        if not previous_version:
            return 1
        return previous_version.version + 1

    def generate_versioned_name_for_file(self) -> str:
        """Generate a filename from the ID and the next version number.

        :return:
            The game slug, map ID hex, and expected next version number.
            e.g. ``ra2_12345678abdc12dc_v01``.
        """
        return f"{self.cnc_game.slug}_{self.id.hex}_v{self.next_version_number():02}"

    def get_map_directory_path(self) -> pathlib.Path:
        """Returns the path to the directory where all files related to the map will be store.

        :return:
            Directory path to put maps and image previews in.
        """
        return pathlib.Path(
            self.cnc_game.slug,
            settings.CNC_MAP_DIRECTORY,
            self.id.hex,
        )

    def set_ban(self, is_banned: bool, banned_by: cnc_user.CncUser) -> None:
        if self.is_legacy:
            raise exceptions.BanException("legacy-maps-cannot-be-banned")
        self.is_banned = is_banned
        self.save(update_fields=["is_banned"])


class CncMapFileManager(models.Manager["CncMapFile"]):
    def find_legacy_map_by_sha1(self, sha1: str) -> t.Union["CncMapFile", None]:
        return super().get_queryset().filter(hash_sha1=sha1, cnc_map__is_mapdb1_compatible=True).first()


class CncMapFile(file_base.CncNetFileBaseModel):
    """Represents the actual map file that a Command & Conquer game reads.

    .. warning::

        ``name`` is auto-generated for this file subclass.
    """

    objects = CncMapFileManager()

    width = models.IntegerField()
    height = models.IntegerField()
    version = models.IntegerField(editable=False)

    cnc_map = models.ForeignKey(CncMap, on_delete=models.CASCADE, null=False)

    ALLOWED_EXTENSION_TYPES = {game_models.CncFileExtension.ExtensionTypes.MAP.value}

    UPLOAD_TYPE = settings.CNC_MAP_DIRECTORY

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cnc_map_id", "version"], name="unique_map_version"),
        ]

    def save(self, *args, **kwargs):
        if not self.version:
            self.version = self.cnc_map.next_version_number()
        self.name = self.cnc_map.generate_versioned_name_for_file()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_upload_to(instance: "CncMapFile", filename: str) -> pathlib.Path:
        """Generate the path to upload map files to.

        Gets called by :func:`kirovy.models.file_base._generate_upload_to` when ``CncMapFile.save`` is called.
        See [the django docs for file fields](https://docs.djangoproject.com/en/5.0/ref/models/fields/#filefield).
        ``upload_to`` is set in :attr:`kirovy.models.file_base.CncNetFileBaseModel.file`, which calls
        ``_generate_upload_to``, which calls this function.

        :param instance:
            Acts as ``self``. The map file object that we are creating an upload path for.
        :param filename:
            The filename of the uploaded file.
        :return:
            Path to upload map to relative to :attr:`~kirovy.settings.base.MEDIA_ROOT`.
        """
        filename = pathlib.Path(filename)
        final_file_name = f"{instance.name}{filename.suffix}"

        # e.g. "yr/maps/CNC_NET_MAP_ID_HEX/ra2_CNC_NET_MAP_ID_HEX_v1.map
        return pathlib.Path(instance.cnc_map.get_map_directory_path(), final_file_name)
