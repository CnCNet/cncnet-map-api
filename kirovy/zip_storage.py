import io
import pathlib
import zipfile

from django.core.files import File
from django.core.files.storage import FileSystemStorage


class ZipFileStorage(FileSystemStorage):
    def save(self, name: str, content: File, max_length: int | None = None):
        if is_zipfile(content):
            return super().save(name, content, max_length)

        internal_filename = pathlib.Path(name).name
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", allowZip64=False, compresslevel=4) as zf:
            content.seek(0)
            zf.writestr(internal_filename, content.read())

        return super().save(f"{name}.zip", zip_buffer, max_length=max_length)


def is_zipfile(file_or_path: File | pathlib.Path) -> bool:
    """Checks if a file is a zip file.

    :param file_or_path:
        The path to a file, or the file itself, to check.
    :returns:
        ``True`` if the file is a zip file.
    """
    try:
        with zipfile.ZipFile(file_or_path, "r") as zf:
            # zf.getinfo("")  # check if zipfile is valid.
            return True
    except zipfile.BadZipfile:
        return False
    except Exception as e:
        raise e
