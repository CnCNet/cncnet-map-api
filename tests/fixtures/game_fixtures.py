import pytest
from kirovy import typing as t, models as k_models, constants


@pytest.fixture
def game_yuri(db) -> k_models.CncGame:
    """Get the Yuri's Revenge ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Yuri's revenge.
    """
    return k_models.CncGame.objects.get(slug=constants.GameSlugs.yuris_revenge)


@pytest.fixture
def game_dune2k(db) -> k_models.CncGame:
    """Get the Dune 2000 ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Dune 2000.
    """
    return k_models.CncGame.objects.get(slug__iexact=constants.GameSlugs.dune_2000)
