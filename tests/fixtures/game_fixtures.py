import pytest
from kirovy import typing as t, models as k_models


@pytest.fixture
def game_yuri(db) -> k_models.CncGame:
    """Get the Yuri's Revenge ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Yuri's revenge.
    """
    return k_models.CncGame.objects.get(slug="yr")
