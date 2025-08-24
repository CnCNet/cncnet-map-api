from functools import cached_property

from django.conf import settings
from django.db import models

from kirovy import exceptions, typing as t

from kirovy.models.cnc_base_model import CncNetBaseModel

__all__ = ["CncFileExtension", "CncGame"]


def is_valid_extension(extension: str) -> None:
    """Validate file extension string.

    :raise exceptions.InvalidFileExtension:
        Raised for invalid file extension strings.
    """
    if not extension.isalnum():
        raise exceptions.InvalidFileExtension(f'"{extension}" is not a valid file extension. Must be alpha only.')


class CncFileExtension(CncNetBaseModel):
    """File extension types for Command & Conquer games and what they do.

    Useful page: https://modenc.renegadeprojects.com/File_Types

    .. note::

        These extension objects are only necessary for user-uploaded files. Don't worry about all of this
        overhead for any files committed to the repository.
    """

    class ExtensionTypes(models.TextChoices):
        """Enum of what kind of file this is to allow for filtering allowed extensions."""

        MAP = "map", "map"
        """This file extensions represents some kind of map file and should be in the map database."""

        ASSETS = "assets", "assets"
        """This file extension represents some kind of game asset to support a map, e.g. a ``.mix`` file."""

        IMAGE = "image", "image"
        """This file extension represents some kind of image uploaded by a user to display on the website."""

    extension = models.CharField(max_length=32, unique=True, validators=[is_valid_extension], blank=False)
    """The actual file extension. Case insensitive but ``.lower()`` will be called all over."""

    about = models.CharField(max_length=2048, null=True, blank=False)
    """An explanation about what this extension does."""

    extension_type = models.CharField(
        max_length=32,
        choices=ExtensionTypes.choices,
        null=False,
        blank=False,
    )

    class Meta:
        indexes = [models.Index(fields=["extension_type"])]

    def save(self, *args, **kwargs):
        self.extension = self.extension.lower()  # Force lowercase
        is_valid_extension(self.extension)  # force validator on save instead from a view.
        super().save(*args, **kwargs)

    @property
    def extension_for_path(self) -> str:
        """Too lazy to format a string with a period? We've got you covered.

        :return:
            Extensions with a ``.`` prefix.
        """
        return f".{self.extension}"


class CncGame(CncNetBaseModel):
    """Represents C&C games and large total-conversion mods like Mental Omega."""

    slug = models.CharField(max_length=16, unique=True)
    """Url and file path slug."""

    full_name = models.CharField(max_length=128)
    """Full display name of the game."""

    is_visible = models.BooleanField(default=False)
    """If true then then this game will appear in the map database website."""

    allow_public_uploads = models.BooleanField(default=False)
    """If true then users with :func:`~kirovy.models.cnc_user.CncUser.can_upload` can upload files for this game.

    Does not affect temporary uploads via the multiplayer lobby.
    """

    compatible_with_parent_maps = models.BooleanField(default=False, null=False, blank=False)
    """If true then the maps from the parent game work in this game. e.g. RA2 maps work in YR."""

    parent_game = models.ForeignKey("self", models.PROTECT, null=True, default=None)
    """If this game is a mod or expansion, then the parent game will be the game the mod / expansion was built on."""

    is_mod = models.BooleanField(default=False)
    """If true then this game is an unofficial mod. e.g. Mental Omega."""

    allowed_extensions = models.ManyToManyField(CncFileExtension)
    """File extensions that this game supports."""

    def save(self, *args, **kwargs):
        self._validate_is_mod()
        super().save(*args, **kwargs)

    def _validate_is_mod(self) -> None:
        """Make sure this mod has a parent game before saving."""
        missing_parent_game = all(
            [x is None for x in [self.parent_game, self.parent_game_id]]
        )  # Django allows just setting the ID, so we need to make sure one of the fields is set.
        if self.is_mod and missing_parent_game:
            raise exceptions.ValidationError("Must specify a parent game for mods.")

    @property
    def allowed_extensions_set(self) -> t.Set[str]:
        """Convenience method to get the extensions as lowercase strings.

        :return:
            The lowercase extensions as a set.
        """
        extensions = self.allowed_extensions.select_related().only("extension").all()
        return {ext.extension.lower() for ext in extensions}

    @cached_property
    def images_relative_url(self) -> str:
        return f"{settings.STATIC_URL}{settings.CNC_GAME_IMAGE_DIRECTORY}"

    @cached_property
    def icon_url(self) -> str:
        return f"{self.images_relative_url}{self.slug}/{self.slug}-icon.png"

    @cached_property
    def logo_url(self) -> str:
        return f"{self.images_relative_url}{self.slug}/logo.png"

    def __repr__(self) -> str:
        return f"<{type(self).__name__} Object: ({self.slug}) '{self.full_name}' [{self.id}]>"
