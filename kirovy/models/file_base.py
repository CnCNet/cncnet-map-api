from django.core import validators
from django.db import models

from kirovy import typing as t, exceptions
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy.models import cnc_game as game_models
from kirovy.utils import file_utils


class CncNetFileBaseModel(CncNetBaseModel):
    class Meta:
        abstract = True

    name = models.CharField(max_length=255, null=False)
    """Filename no extension."""

    file = models.FileField(null=False)
    """The actual file this object represent."""

    file_extension = models.ForeignKey(
        game_models.CncFileExtension, on_delete=models.PROTECT
    )
    """What type of file extension this object is."""

    cnc_game = models.ForeignKey(game_models.CncGame, models.PROTECT, null=False)
    """Which game does this file belong to. Needed for file validation."""

    hash_md5 = models.CharField(max_length=32, null=False)
    """Used for checking exact file duplicates."""

    hash_sha512 = models.CharField(max_length=512, null=False)
    """Used for checking exact file duplicates."""

    ALLOWED_EXTENSION_TYPES = set(game_models.CncFileExtension.ExtensionTypes.values)

    def __init__(self, *args, **kwargs):
        super(CncNetFileBaseModel, self).__init__(*args, **kwargs)
        self.validate_file_extension(self.file_extension)

    def validate_file_extension(
        self, file_extension: game_models.CncFileExtension
    ) -> None:
        if file_extension.extension.lower() not in self.cnc_game.allowed_extensions_set:
            raise validators.ValidationError(
                f'"{file_extension.extension}" is not a valid file extension for game "{self.cnc_game.full_name}".'
            )
        if file_extension.extension_type not in self.ALLOWED_EXTENSION_TYPES:
            raise exceptions.InvalidFileExtension(
                f'"{file_extension.extension}" is not a valid file extension for this upload type.'
            )

    def save(self, *args, **kwargs):
        self.hash_md5 = file_utils.hash_file_md5(self.file)
        self.hash_sha512 = file_utils.hash_file_sha512(self.file)

    @property
    def allowed_extensions_set(self) -> t.Set[str]:
        return self.cnc_game.allowed_extensions_set
