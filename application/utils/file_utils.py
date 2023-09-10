import hashlib
from functools import partial

from django.db.models.fields.files import FieldFile


def hash_file_md5(file: FieldFile, block_size=65536) -> str:
    return _hash_file(hashlib.md5(), file, block_size)


def hash_file_sha512(file: FieldFile, block_size=65536) -> str:
    return _hash_file(hashlib.sha512(), file, block_size)


def _hash_file(hasher: "_HASH", file: FieldFile, block_size: int) -> str:
    with file.open("rb") as f:
        for buf in iter(partial(f.read, block_size), b""):
            hasher.update(buf)

    return hasher.hexdigest()
