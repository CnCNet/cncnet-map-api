import collections
import functools
import hashlib
import pathlib
import struct
import zipfile
from collections.abc import Buffer

from django.core.files import File

from kirovy import typing as t


def hash_file_md5(file: File, block_size=65536) -> str:
    return _hash_file(hashlib.md5(), file, block_size)


def hash_file_sha512(file: File, block_size=65536) -> str:
    return _hash_file(hashlib.sha512(), file, block_size)


def hash_file_sha1(file: File, block_size=65536) -> str:
    return _hash_file(hashlib.sha1(), file, block_size)


def _hash_file(hasher: "_HASH", file: File, block_size: int) -> str:
    file.seek(0)
    file_contents = file.read()
    if isinstance(file_contents, str):
        file_contents = file_contents.encode()
    hasher.update(file_contents)
    file.seek(0)

    return hasher.hexdigest()


class ByteSized:
    """A class to pretty format byte sizes, inspired by ``datetime.timedelta``'s functionality."""

    _byte: int = 0
    _kilo: int = 0
    _mega: int = 0
    _giga: int = 0
    _tera: int = 0

    def __new__(
        cls,
        byte: int = 0,
        *,
        kilo: int = 0,
        mega: int = 0,
        giga: int = 0,
        tera: int = 0,
    ) -> "ByteSized":

        if any([x < 0 for x in [tera, giga, mega, kilo, byte]]):
            raise AttributeError("Does not support args < 0")

        self = object.__new__(cls)
        b2k, br = divmod(byte, 1000)
        self._byte = br

        kilo = kilo + b2k
        k2m, kr = divmod(kilo, 1000)
        self._kilo = kr

        mega = mega + k2m
        m2g, mr = divmod(mega, 1000)
        self._mega = mr

        giga = giga + m2g
        g2t, gr = divmod(giga, 1000)
        self._giga = gr

        self._tera = tera + g2t

        return self

    def __str__(self) -> str:
        return ", ".join([f"{size}{desc}" for desc, size in self.__mapping.items() if size > 0])

    @functools.cached_property
    def __mapping(self) -> t.Dict[str, int]:
        return collections.OrderedDict(
            {
                "TB": self.tera,
                "GB": self.giga,
                "MB": self.mega,
                "KB": self.kilo,
                "B": self.byte,
            }
        )

    @property
    def tera(self) -> int:
        return self._tera

    @property
    def giga(self) -> int:
        return self._giga

    @property
    def mega(self) -> int:
        return self._mega

    @property
    def kilo(self) -> int:
        return self._kilo

    @property
    def byte(self) -> int:
        return self._byte

    @functools.cached_property
    def total_bytes(self) -> int:
        total = 0
        to_explode = [self._byte, self._kilo, self._mega, self._giga, self._tera]
        for i, value in enumerate(to_explode):
            exponent = 3 * i
            magnitude = 10**exponent
            total += value * magnitude
        return total

    def __gt__(self, other: "ByteSized") -> bool:
        return self.total_bytes > other.total_bytes

    def __lt__(self, other: "ByteSized") -> bool:
        return self.total_bytes < other.total_bytes

    def __ge__(self, other: "ByteSized") -> bool:
        return self.total_bytes >= other.total_bytes

    def __le__(self, other: "ByteSized") -> bool:
        return self.total_bytes <= other.total_bytes

    def __eq__(self, other: "ByteSized") -> bool:
        return self.total_bytes == other.total_bytes


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


def flat_unpack(format: str, data: Buffer) -> t.List[t.Any]:
    """Unpack a buffer iteratively.

    :param format:
        See `Format docs <https://docs.python.org/3.12/library/struct.html#format-strings>`_
    :param data:
        The data to unpack.
    :return:
        A list of objects of the type specified by ``format``.
    :raises struct.error:
        This will be raised if ``data`` cannot be unpacked to the expected ``format``.
    """
    return [x[0] for x in struct.iter_unpack(format, data)]
