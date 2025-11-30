import pytest

from kirovy import typing as t, models as k_models


@pytest.fixture
def extension_map(db) -> k_models.CncFileExtension:
    """Get the ``.map`` file extension object.

    This fixture depends on the game data migration being run.

    The actual file extension, e.g. ``.exe``, is stored in :attr:`kirovy.models.cnc_game.CncFileExtension.extension`.

    :return:
        The extension object for .map files.
    """
    return k_models.CncFileExtension.objects.get(extension="map")


@pytest.fixture
def extension_mix(db) -> k_models.CncFileExtension:
    """Get the mix file extension object.

    This fixture depends on the game data migration being run.

    :return:
        The extension object for .mix files.
    """
    return k_models.CncFileExtension.objects.get(extension="mix")


@pytest.fixture
def create_cnc_file_extension(db):
    """Return a function to create a CNC file extension."""

    def _inner(
        extension: str = "map",
        about: str = "A Generals map file.",
        extension_type: k_models.CncFileExtension.ExtensionTypes = k_models.CncFileExtension.ExtensionTypes.MAP,
    ) -> k_models.CncFileExtension:
        """Create a CNC file extension.

        :param extension:
            The actual file extension at the end of a filepath. Don't include the `.` prefix.
        :param about:
            A description of the file extension.
        :param extension_type:
            The type of file extension.
        :return:
            A CNC file extension object.
        """
        file_extension = k_models.CncFileExtension(extension=extension, about=about, extension_type=extension_type)
        file_extension.save()
        file_extension.refresh_from_db()
        return file_extension

    return _inner


@pytest.fixture
def cnc_file_extension(create_cnc_file_extension) -> k_models.CncFileExtension:
    """Convenience wrapper to make a CncFileExtension for a test."""
    return create_cnc_file_extension()
