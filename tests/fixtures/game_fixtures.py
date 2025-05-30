import pytest
from kirovy import typing as t, constants
from kirovy.models.cnc_game import CncGame


@pytest.fixture
def game_yuri(db) -> CncGame:
    """Get the Yuri's Revenge ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Yuri's revenge.
    """
    return CncGame.objects.get(slug=constants.GameSlugs.yuris_revenge)


@pytest.fixture
def game_dune2k(db) -> CncGame:
    """Get the Dune 2000 ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Dune 2000.
    """
    return CncGame.objects.get(slug__iexact=constants.GameSlugs.dune_2000)


@pytest.fixture
def game_tiberian_dawn(db) -> CncGame:
    """Get the Tiberian Dawn ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Tiberian Dawn.
    """
    return CncGame.objects.get(slug__iexact=constants.GameSlugs.tiberian_dawn)


@pytest.fixture
def game_tiberian_sun(db) -> CncGame:
    """Get the Tiberian Sun ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Tiberian Sun.
    """
    return CncGame.objects.get(slug__iexact=constants.GameSlugs.tiberian_sun)


@pytest.fixture
def game_dawn_of_the_tiberium_age(db) -> CncGame:
    """Get the Dawn Of The Tiberium Age ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Dawn Of The Tiberium Age.
    """
    return CncGame.objects.get(slug__iexact=constants.GameSlugs.dawn_of_the_tiberium_age)


@pytest.fixture
def game_red_alert(db) -> CncGame:
    """Get the Red Alert ``CncGame``.

    This fixture depends on the game data migration being run.

    :return:
        The game object for Red Alert.
    """
    return CncGame.objects.get(slug__iexact=constants.GameSlugs.red_alert)
