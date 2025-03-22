from kirovy.constants import GameSlugs
from kirovy.constants.api_codes import LegacyUploadApiCodes
from kirovy.exceptions import view_exceptions
from kirovy.services.legacy_upload import westwood, dune_2000
from kirovy.services.legacy_upload.base import LegacyMapServiceBase
from kirovy import typing as t


_GAME_LEGACY_SERVICE_MAP: t.Dict[str, t.Type[LegacyMapServiceBase]] = {
    GameSlugs.yuris_revenge.value: westwood.YurisRevengeLegacyMapService,
    GameSlugs.dune_2000.value: dune_2000.Dune2000LegacyMapService,
}


def get_legacy_service_for_slug(game_slug: str) -> t.Type[LegacyMapServiceBase]:
    if service := _GAME_LEGACY_SERVICE_MAP.get(game_slug):
        return service

    raise view_exceptions.KirovyValidationError(
        "Game not supported on legacy endpoint",
        code=LegacyUploadApiCodes.GAME_NOT_SUPPORTED,
        additional={"supported": _GAME_LEGACY_SERVICE_MAP.keys()},
    )
