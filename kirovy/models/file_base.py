import pathlib

from django.core import validators
from django.db import models

from kirovy import typing as t, exceptions
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy.models import cnc_game as game_models
from kirovy.utils import file_utils


def _generate_upload_to(
    instance: "CncNetFileBaseModel", filename: t.Union[str, pathlib.Path]
) -> pathlib.Path:
    """Calls the subclass specific method to generate an upload path.

    Do **NOT** override this function. Override the ``generate_upload_to`` function on your file model.

    :param instance:
        The instance of the object we're saving a file for.
    :param filename:
        The uploaded file name.
    :return:
        The path where the object should be stored.
    """
    return instance.generate_upload_to(instance, filename)


class CncNetFileBaseModel(CncNetBaseModel):
    class Meta:
        abstract = True

    UPLOAD_TYPE = "uncategorized_uploads"
    """:attr: The directory, underneath the game slug, where all files for this class will be stored."""

    name = models.CharField(max_length=255, null=False, blank=False)
    """Filename no extension."""

    file = models.FileField(null=False, upload_to=_generate_upload_to)
    """The actual file this object represent."""

    file_extension = models.ForeignKey(
        game_models.CncFileExtension,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )
    """What type of file extension this object is."""

    ALLOWED_EXTENSION_TYPES = set(game_models.CncFileExtension.ExtensionTypes.values)
    """Used to make sure e.g. a ``.mix`` doesn't get uploaded as a ``CncMapFile``.

    These are checked against :attr:`kirovy.models.cnc_game.CncFileExtension.extension_type`.
    """

    cnc_game = models.ForeignKey(
        game_models.CncGame, models.PROTECT, null=False, blank=False
    )
    """Which game does this file belong to. Needed for file validation."""

    hash_md5 = models.CharField(max_length=32, null=False, blank=False)
    """Used for checking exact file duplicates."""

    hash_sha512 = models.CharField(max_length=512, null=False, blank=False)
    """Used for checking exact file duplicates."""

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
        self.validate_file_extension(self.file_extension)
        self.hash_md5 = file_utils.hash_file_md5(self.file)
        self.hash_sha512 = file_utils.hash_file_sha512(self.file)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_upload_to(
        instance: "CncNetFileBaseModel", filename: str
    ) -> pathlib.Path:
        """Generate the base upload path.

        This is where files will go if a class doesn't set its own ``generate_upload_to``.

        :param instance:
            The instance that we're saving a file for.
        :param filename:
            The file name that was uploaded.
        :return:
            The path to save the file to.
        """
        if not isinstance(filename, pathlib.Path):
            filename = pathlib.Path(filename)

        # e.g. "yr/uncategorized_uploads/SOME_ID/alex_instructions.docx
        return pathlib.Path(
            instance.cnc_game.slug,
            instance.UPLOAD_TYPE,
            str(instance.id),
            filename.name,
        )
