from django.db import models
from django.conf import settings

from application import constants, exceptions

from django.utils.translation import gettext as _


class CncGame(models.Model):
    """Represents C&C games and large total-conversion mods like Mental Omega."""

    slug = models.CharField(max_length=16)
    full_name = models.CharField(max_length=64)
    is_visible = models.BooleanField(default=False)
    allow_public_uploads = models.BooleanField(default=False)
    icon_file_name = models.ImageField(upload_to=constants.cnc_game_icon_directory)
    parent_game = models.ForeignKey("self", models.PROTECT, null=True, default=None)
    is_mod = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self._validate_is_mod()
        super().save(*args, **kwargs)

    def _validate_is_mod(self) -> None:
        missing_parent_game = all(
            [x is None for x in [self.parent_game, self.parent_game_id]]
        )
        if self.is_mod and missing_parent_game:
            raise exceptions.ValidationError("Must specify a parent game for mods.")
