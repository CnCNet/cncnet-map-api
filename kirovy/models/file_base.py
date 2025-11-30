import pathlib

from django.db import models

from kirovy import typing as t
from kirovy.models import cnc_game as game_models
from kirovy.models.cnc_game import GameScopedUserOwnedModel
from kirovy.utils import file_utils
from kirovy.zip_storage import ZipFileStorage


def default_generate_upload_to(instance: "CncNetFileBaseModel", filename: t.Union[str, pathlib.Path]) -> pathlib.Path:
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


class CncNetFileBaseModel(GameScopedUserOwnedModel):
    class Meta:
        abstract = True

    UPLOAD_TYPE = "uncategorized_uploads"
    """:attr: The directory, underneath the game slug, where all files for this class will be stored."""

    name = models.CharField(max_length=255, null=False, blank=False)
    """Filename no extension."""

    file = models.FileField(null=False, upload_to=default_generate_upload_to, max_length=2048)
    """The actual file this object represent. The max length of 2048 is half of the unix max."""

    file_extension = models.ForeignKey(
        game_models.CncFileExtension,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )
    """What type of file extension this object is."""

    ALLOWED_EXTENSION_TYPES: t.Set[str] = set(game_models.CncFileExtension.ExtensionTypes.values)
    """Used to make sure e.g. a ``.mix`` doesn't get uploaded as a ``CncMapFile``.

    These are checked against :attr:`kirovy.models.cnc_game.CncFileExtension.extension_type`.
    """

    hash_md5 = models.CharField(max_length=32, null=False, blank=False)
    """Used for checking exact file duplicates."""

    hash_sha512 = models.CharField(max_length=512, null=False, blank=False)
    """Used for checking exact file duplicates."""

    hash_sha1 = models.CharField(max_length=50, null=True, blank=False)
    """Backwards compatibility with the old CncNetClient."""

    def validate_file_extension(self, file_extension: game_models.CncFileExtension) -> None:
        """Validate that an extension is supported for a game.

        This should probably be done in a serializer, but doing it all the way down in the model is
        technically safer to avoid screwing things up in a migration.
        """
        # Images are allowed for all games.
        is_image = self.file_extension.extension_type == self.file_extension.ExtensionTypes.IMAGE
        is_allowed_for_game = file_extension.extension.lower() in self.cnc_game.allowed_extensions_set

        from kirovy.exceptions.view_exceptions import KirovyValidationError

        if not is_allowed_for_game and not is_image:
            raise KirovyValidationError(
                detail=f'"{file_extension.extension.lower()}" is not a valid file extension for game "{self.cnc_game.full_name}".',
                code="file-extension-unsupported-for-game",
            )
        if file_extension.extension_type not in self.ALLOWED_EXTENSION_TYPES:
            raise KirovyValidationError(
                detail=f'"{file_extension.extension}" is not a valid file extension for this upload type.',
                code="file-extension-unsupported-for-model",
            )

    def save(self, *args, **kwargs):
        self.validate_file_extension(self.file_extension)

        if not self.hash_md5:
            self.hash_md5 = file_utils.hash_file_md5(self.file)
        if not self.hash_sha512:
            self.hash_sha512 = file_utils.hash_file_sha512(self.file)
        if not self.hash_sha1:
            self.hash_sha1 = file_utils.hash_file_sha1(self.file)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_upload_to(instance: "CncNetFileBaseModel", filename: str) -> pathlib.Path:
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


class CncNetZippedFileBaseModel(CncNetFileBaseModel):
    """A base file class that will zip and unzip the ``file`` attribute.

    Do **not** use this class for files that will be directly accessed via hyperlink.
    e.g. don't use this class for images.
    """

    class Meta:
        abstract = True

    file = models.FileField(null=False, upload_to=default_generate_upload_to, storage=ZipFileStorage)
