from django.core import validators
from django.db import models

from application import typing


class CncNetFileBaseModel(models.Model):
    class Meta:
        abstract = True

    UPLOAD_TO = "generic"
    ALLOWED_EXTENSIONS = []

    name = models.CharField(max_length=255, null=True)
    file = models.FileField(upload_to=UPLOAD_TO, null=True)
    file_extension = models.CharField(
        max_length=64,
        null=True,
    )

    hash_md5 = models.CharField(max_length=32)
    hash_sha512 = models.CharField(max_length=512)

    def __init__(self, *args, **kwargs):
        super(CncNetFileBaseModel, self).__init__(*args, **kwargs)
        self.validate_file_extension(self.file_extension)

    def validate_file_extension(self, file_extension: typing.FileExtension) -> None:
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise validators.ValidationError(
                f'"{file_extension}" is not a valid file extension.'
            )
