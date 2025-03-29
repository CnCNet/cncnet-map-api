import io
import pathlib
import zipfile
from collections.abc import Generator
from typing import Any

from django.core.files.base import ContentFile

from kirovy import typing as t

import pytest
from django.core.files import File

from kirovy.utils import file_utils


class ReadOnlyFile(File):
    def write(self, s, /):
        raise Exception("Don't tamper with the test files.")


@pytest.fixture
def test_data_path() -> pathlib.Path:
    """The path to the directory where we store testing data files, e.g. a test map."""
    return pathlib.Path(__file__).parent.parent / "test_data"


@pytest.fixture
def load_test_file(test_data_path):
    """Return a function to load a file from test_data."""

    def _inner(relative_path: t.Union[str, pathlib.Path], read_mode: str = "rb") -> File:
        """Load a file from test_data.

        :param relative_path:
            The filename or the path object of the filename for a file in ``cncnet_map_api/tests/test_data/``
        :return:
            A django file object.
        """
        full_path = test_data_path / relative_path

        return ReadOnlyFile(open(full_path, read_mode))

    return _inner


@pytest.fixture
def file_binary(load_test_file) -> Generator[File, Any, None]:
    """Returns a random binary file."""
    file = load_test_file("binary_file.mp3", "rb")
    yield file
    file.close()


@pytest.fixture
def file_map_valid(load_test_file) -> Generator[File, Any, None]:
    """Returns a valid .map file that was made in Final Alert 2 and has a preview."""
    file = load_test_file("test_ra2yr.map")
    yield file
    file.close()


@pytest.fixture
def file_map_snow(load_test_file) -> Generator[File, Any, None]:
    file = load_test_file("non_divisible_by_four.yrm")
    yield file
    file.close()


@pytest.fixture
def file_map_desert(load_test_file) -> Generator[File, None, None]:
    file = load_test_file("desert.map")
    yield file
    file.close()


@pytest.fixture
def file_map_cant_parse(load_test_file) -> Generator[File, Any, None]:
    """Return a text file that is not valid INI."""
    file = load_test_file("map_file_cant_parse_as_ini.map")
    yield file
    file.close()


@pytest.fixture
def file_map_missing_sections(load_test_file) -> Generator[File, Any, None]:
    """Return a valid INI file that is missing required map sections."""
    file = load_test_file("map_file_missing_sections.map")
    yield file
    file.close()


@pytest.fixture
def file_map_unfair(load_test_file) -> Generator[File, Any, None]:
    """Return a valid map that is very unfair and qualifies as a cheat map."""
    file = load_test_file("totally_fair_map.map")
    yield file
    file.close()


@pytest.fixture
def file_map_dune2k(load_test_file) -> Generator[File, Any, None]:
    """Return a valid zip file for a dune 2k mpa.

    Map name is ``Ornithopter Fringe``.

    Original CnCNet hash is ``f9270d1e17e832a694dcd8c07e3acbb96a578a18``
    """
    file = load_test_file("dune2000/f9270d1e17e832a694dcd8c07e3acbb96a578a18.zip")
    yield file
    file.close()


@pytest.fixture
def file_map_ts_woodland_hills(load_test_file) -> Generator[File, Any, None]:
    """Return a valid Tiberian Sun map.

    Map name is ``Woodland Hills``.

    Original CnCNet hash is ``309fb5d6e2042e48b22f4ced910c0c174a53597f``.
    """
    file = load_test_file("tiberian_sun/ts_woodland_hills.map")
    yield file
    file.close()


@pytest.fixture
def file_map_dta_peace_and_war(load_test_file) -> Generator[File, Any, None]:
    """Return a valid Dawn Of The Tiberium Age map.

    Map name is ``Peace And War``.

    Original CnCNet hash is ``71b9f8a031827cccb3cdf2273dedc44a44e06706``.
    """
    file = load_test_file("tiberian_sun/dta_peace_and_war.map")
    yield file
    file.close()


@pytest.fixture
def file_map_ra_d_day(load_test_file) -> Generator[File, Any, None]:
    """Return a valid Red Alert map.

    Map name is ``D Day``.

    Original CnCNet hash is ``1a4f34f61c90dbff5031e3fbd9780b3ed162a7cb``.
    """
    file = load_test_file("red_alert/ra_d_day.mpr")
    yield file
    file.close()


ZipContentsSha1 = str


@pytest.fixture
def zip_map_for_legacy_upload():
    """Returns a function to zip a map in the same way as legacy CnCNet clients.

    Use this for testing endpoints that are backwards compatible with map db 1.0.
    """

    def _inner(file: File | io.BytesIO) -> t.Tuple[ContentFile, ZipContentsSha1]:
        # The legacy map db required zip files to be the sha1 of the zip file's contents.
        file_sha1 = file_utils.hash_file_sha1(file)
        # Create a zip file in memory, and write the map file to it.
        zip_bytes = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_bytes, mode="w")
        zip_file.writestr(file.name, file.read())
        # ``.close`` writes all zip metadata to the stream.
        zip_file.close()
        zip_bytes.seek(0)

        # We need a django-friendly file handler, so read the byte-stream into a django file.
        return ContentFile(zip_bytes.read(), f"{file_sha1}.zip"), file_sha1

    return _inner
