from kirovy.models import CncGame
from kirovy.models.cnc_map import CncMap, CncMapFile, MapCategory
from kirovy import typing as t
import pytest


@pytest.fixture
def create_cnc_map_category(db):
    """Return a function to create a map category."""

    def _inner(
        name: str = "Halo Gen",
    ) -> MapCategory:
        """Create a map category.

        :param name:
            The category name, should match game modes, or be something like e.g. "Mission".
            Game modes are store in map file INI under ``Basic.GameMode``.
            The slug gets generated from this name
        :return:
            A category that can be used to create :class:`kirovy.models.cnc_map.CncMap` objects.
        """
        category = MapCategory(name=name)
        category.save()
        category.refresh_from_db()
        return category

    return _inner


@pytest.fixture
def cnc_map_category(create_cnc_map_category) -> MapCategory:
    """Convenience wrapper to make a MapCategory for a test."""
    return create_cnc_map_category()


@pytest.fixture
def create_cnc_map(db, cnc_map_category, game_yuri):
    """Return a function to create a CncMap object."""

    def _inner(
        map_name: str = "Streets Of Gold 2",
        description: str = "A fun map. Capture the center airports for a Hind.",
        cnc_game: CncGame = game_yuri,
        map_categories: t.List[MapCategory] = None,
    ) -> CncMap:
        """Create a CncMap object.

        :param map_name:
            Name of the map that would appear on the site. e.g. "Alex's Very Balanced Map".
        :param description:
            Description that's appear on the site, e.g. "Map balanced around making Alex win."
        :param cnc_game:
            The game that this map belongs to.
        :param map_categories:
            The categories the map falls under. These can be found in the map file INI
            for the 2d C&C games. ``Basic.GameMode``. Many-to-many
        :return:
            A ``CncMap`` object that can be used to create :class:`kirovy.models.cnc_map.CncMapFile` objects in tests.
        """
        if not map_categories:
            map_categories = [
                cnc_map_category,
            ]

        cnc_map = CncMap(
            cnc_game=cnc_game,
            description=description,
            map_name=map_name,
        )
        cnc_map.save()
        cnc_map.categories.add(*map_categories)
        cnc_map.refresh_from_db()
        cnc_map.categories.prefetch_related()

        return cnc_map

    return _inner


@pytest.fixture
def cnc_map(create_cnc_map) -> CncMap:
    """Convenience wrapper to make a CncMap for a test."""
    return create_cnc_map()
