from django.core import validators
from django.db import models

from kirovy import typing
from kirovy.utils import file_utils


class CncNetFileBaseModel(models.Model):
    class Meta:
        abstract = True

    UPLOAD_TO = "generic/"
    ALLOWED_EXTENSIONS = []

    name = models.CharField(max_length=255, null=False)
    file = models.FileField(upload_to=UPLOAD_TO, null=False)
    file_extension = models.CharField(
        max_length=64,
        null=False,
    )

    hash_md5 = models.CharField(max_length=32, null=False)
    hash_sha512 = models.CharField(max_length=512, null=False)

    def __init__(self, *args, **kwargs):
        super(CncNetFileBaseModel, self).__init__(*args, **kwargs)
        self.validate_file_extension(self.file_extension)

    def validate_file_extension(self, file_extension: typing.FileExtension) -> None:
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise validators.ValidationError(
                f'"{file_extension}" is not a valid file extension.'
            )

    def save(self, *args, **kwargs):
        self.hash_md5 = file_utils.hash_file_md5(self.file)
        self.hash_sha512 = file_utils.hash_file_sha512(self.file)
