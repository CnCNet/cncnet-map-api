from django.db.models import UUIDField

from kirovy.models import CncGame, CncUser
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
def create_cnc_map(db, cnc_map_category, game_yuri, client_user):
    """Return a function to create a CncMap object."""

    def _inner(
        map_name: str = "Streets Of Gold 2",
        description: str = "A fun map. Capture the center airports for a Hind.",
        cnc_game: CncGame = game_yuri,
        map_categories: t.List[MapCategory] = None,
        user_id: t.Union[UUIDField, str, None, t.NO_VALUE] = t.NO_VALUE,
        is_legacy: bool = False,
        is_published: bool = True,
        is_banned: bool = False,
        is_reviewed: bool = False,
        is_temporary: bool = False,
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
        :param user_id:
            The user who owns the map. ``None`` is a valid option.
            Defaults to the user from the :func:`~tests.fixtures.common_fixtures.client_user` fixture.
        :param is_legacy:
            If true, this is a map copied from the old map database. Has a potential to be garbage, or a holy relic.
        :param is_published:
            If true, the map author has decided to make their map publicly visible.
        :param is_banned:
            If true, the map has been banned from all list views.
        :param is_reviewed:
            If true, a staff member has reviewed this map.
        :param is_temporary:
            If true, then this map was uploaded by the CnCNet client, and is only visible to the client.
            Will only be available through direct links for a limited time.
        :return:
            A ``CncMap`` object that can be used to create :class:`kirovy.models.cnc_map.CncMapFile` objects in tests.
        """
        if user_id is t.NO_VALUE:
            user_id = client_user.kirovy_user.id
        if not map_categories:
            map_categories = [
                cnc_map_category,
            ]

        cnc_map = CncMap(
            cnc_game=cnc_game,
            description=description,
            map_name=map_name,
            is_legacy=is_legacy,
            cnc_user_id=user_id,
            is_published=is_published,
            is_banned=is_banned,
            is_reviewed=is_reviewed,
            is_temporary=is_temporary,
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
