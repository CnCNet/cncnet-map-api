import io
import pathlib
import zipfile

from django.core.files import File
from django.core.files.storage import FileSystemStorage

from kirovy.utils import file_utils


class ZipFileStorage(FileSystemStorage):
    def save(self, name: str, content: File, max_length: int | None = None):
        if file_utils.is_zipfile(content):
            return super().save(name, content, max_length)

        internal_extension = pathlib.Path(name).suffix
        internal_filename = file_utils.hash_file_sha1(content) + internal_extension
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", allowZip64=False, compresslevel=4) as zf:
            content.seek(0)
            zf.writestr(internal_filename, content.read())

        return super().save(f"{name}.zip", zip_buffer, max_length=max_length)
