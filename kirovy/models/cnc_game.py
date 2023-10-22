from functools import cached_property

from django.conf import settings
from django.db import models

from kirovy import exceptions

from kirovy.models.cnc_base_model import CncNetBaseModel


class CncGame(CncNetBaseModel):
    """Represents C&C games and large total-conversion mods like Mental Omega."""

    slug = models.CharField(max_length=16, unique=True)
    """Url and file path slug."""

    full_name = models.CharField(max_length=128)
    """Full display name of the game."""

    is_visible = models.BooleanField(default=False)
    """If true then then this game will appear in the map database website."""

    allow_public_uploads = models.BooleanField(default=False)
    """If true then users with :func:`~kirovy.models.cnc_user.CncUser.can_upload` can upload files for this game."""

    compatible_with_parent_maps = models.BooleanField(default=False, null=False)
    """If true then the maps from the parent game work in this game. e.g. RA2 maps work in YR."""

    parent_game = models.ForeignKey("self", models.PROTECT, null=True, default=None)
    """If this game is a mod or expansion, then the parent game will be the game the mod / expansion was built on."""

    is_mod = models.BooleanField(default=False)
    """If true then this game is an unofficial mod. e.g. Mental Omega."""

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

    @cached_property
    def images_relative_url(self) -> str:
        return f"{settings.STATIC_URL}{settings.CNC_GAME_IMAGE_DIRECTORY}"

    @cached_property
    def icon_url(self) -> str:
        return f"{self.images_relative_url}{self.slug}/{self.slug}-icon.png"

    @cached_property
    def logo_url(self) -> str:
        return f"{self.images_relative_url}{self.slug}/logo.png"
