import pathlib
from collections.abc import Generator
from typing import Any

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
    """Return a valid zip file for a dune 2k mpa."""
    file = load_test_file("valid_dune_map.zip")
    yield file
    file.close()


@pytest.fixture
def rename_file_for_legacy_upload():
    """Returns a function to rename a file for upload to a legacy endpoint."""

    def _inner(file: File) -> File:
        assert file.name.endswith(".zip"), "Only zip files can be sent to legacy endpoints."
        # Uploads to legacy endpoints need the hash name
        file.name = file_utils.hash_file_sha1(file) + ".zip"
        return file

    return _inner
