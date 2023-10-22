import pytest

from kirovy import typing as t, models as k_models


@pytest.fixture
def extension_map(db) -> k_models.CncFileExtension:
    """Get the map file extension object.

    This fixture depends on the game data migration being run.

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
