from django.core.files import File
from django.db.models import UUIDField

from kirovy.models import CncGame, CncUser
from kirovy.models.cnc_map import CncMap, CncMapFile, MapCategory
from kirovy import typing as t
import pytest

from kirovy.services.cnc_gen_2_services import CncGen2MapParser, CncGen2MapSections
from kirovy.utils import file_utils


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
def create_cnc_map_file(db, extension_map, zip_map_for_legacy_upload):
    def _inner(
        file: File,
        cnc_map: CncMap,
        zip_for_legacy: bool = False,
    ) -> CncMapFile:
        file_to_save = file
        if zip_for_legacy:
            file_to_save, _ = zip_map_for_legacy_upload(file_to_save)
        map_parser = CncGen2MapParser(file)
        map_file = CncMapFile(
            width=map_parser.ini.get(CncGen2MapSections.HEADER, "Width"),
            height=map_parser.ini.get(CncGen2MapSections.HEADER, "Height"),
            file=file_to_save,
            file_extension=extension_map,
            cnc_game_id=cnc_map.cnc_game_id,
            hash_md5=file_utils.hash_file_md5(file),
            hash_sha512=file_utils.hash_file_sha512(file),
            hash_sha1=file_utils.hash_file_sha1(file),
            cnc_map_id=cnc_map.id,
        )

        map_file.save()
        map_file.refresh_from_db()
        # Reset the seek in case other fixtures, or the test, need to use the file.
        # This also prevents issues from fixtures and tests using the same file fixture.
        file.seek(0)
        return map_file

    return _inner


@pytest.fixture
def create_cnc_map(db, cnc_map_category, game_yuri, client_user, create_cnc_map_file):
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
        file: File | None = None,
        is_mapdb1_compatible: bool = False,
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
        :param file:
            A map file to include. Defaults to ``None`` for the sake of speed.
        :param is_mapdb1_compatible:
            If true, then this map is compatible with map db 1.0 and can be downloaded via ``/{game_slug}/{sha1}.zip``
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
            is_mapdb1_compatible=is_mapdb1_compatible,
        )
        cnc_map.save()
        cnc_map.categories.add(*map_categories)
        cnc_map.refresh_from_db()
        cnc_map.categories.prefetch_related()

        if file:
            create_cnc_map_file(file=file, cnc_map=cnc_map)

        return cnc_map

    return _inner


@pytest.fixture
def cnc_map(create_cnc_map) -> CncMap:
    """Convenience wrapper to make a CncMap for a test."""
    return create_cnc_map()


@pytest.fixture
def banned_cheat_map(create_cnc_map, file_map_unfair) -> CncMap:
    """A map cheat map that was uploaded via the CnCNet client, then banned."""
    return create_cnc_map(
        is_banned=True,
        is_temporary=True,
        file=file_map_unfair,
    )
