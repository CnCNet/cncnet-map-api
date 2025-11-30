import pytest
from kirovy import typing as t, constants
from kirovy.models.cnc_game import CncGame, CncFileExtension


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


@pytest.fixture
def create_cnc_game(db, extension_map, extension_mix):
    """Return a function to create a CNC game."""

    def _inner(
        slug: str = "ra2remaster",
        full_name: str = "Command & Conquer: Red Alert 2 - Remastered",
        is_visible: bool = True,
        allow_public_uploads: bool = True,
        compatible_with_parent_maps: bool = False,
        parent_game: CncGame | None = None,
        is_mod: bool = False,
        allowed_extensions: t.List[CncFileExtension] | None = None,
    ) -> CncGame:
        """Create a CNC game.

        :param slug:
            The slug for the game.
        :param full_name:
            The full name of the game.
        :param is_visible:
            If the game is visible on the website.
        :param allow_public_uploads:
            If users can upload maps for this game.
        :param compatible_with_parent_maps:
            If maps from the parent game work in this game.
        :param parent_game:
            The parent game if this is a mod or expansion.
        :param is_mod:
            If this is a mod.
        :return:
            A CNC game object.
        """
        if allowed_extensions is None:
            allowed_extensions = [extension_mix, extension_map]
        game = CncGame(
            slug=slug,
            full_name=full_name,
            is_visible=is_visible,
            allow_public_uploads=allow_public_uploads,
            compatible_with_parent_maps=compatible_with_parent_maps,
            parent_game=parent_game,
            is_mod=is_mod,
        )
        game.save()
        game.allowed_extensions.add(*allowed_extensions)
        game.refresh_from_db()
        return game

    return _inner


@pytest.fixture
def cnc_game(create_cnc_game) -> CncGame:
    """Convenience wrapper to make a CncGame for a test."""
    return create_cnc_game()


@pytest.fixture
def game_uploadable(create_cnc_game) -> CncGame:
    return create_cnc_game(is_visible=True, allow_public_uploads=True)
