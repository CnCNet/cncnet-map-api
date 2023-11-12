import pathlib

from kirovy import typing as t


def find_fixture_modules() -> t.List[str]:
    """Get all fixture modules in the fixtures directory.

    Don't add ``__init__.py`` files to ``tests`` or ``tests/fixtures`` or this breaks.

    :return:
        Fixture module names.
    """
    tests_dir = pathlib.Path(__file__).parent
    fixtures_dir = pathlib.Path(tests_dir, "fixtures")
    files = pathlib.Path(fixtures_dir).glob("*_fixtures.py")

    fixture_modules = [f"fixtures.{file.stem}" for file in files]
    return fixture_modules


fixtures = find_fixture_modules()
other_plugins: t.List[str] = []

pytest_plugins = fixtures + other_plugins
