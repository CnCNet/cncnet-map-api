from kirovy import typing as t, exceptions as e
from kirovy.constants import GameEngines
from kirovy.models import CncGame
from kirovy.services.cnc_gen_2_services import CncGen2MapParser


def get_map_parser_for_game(game: CncGame) -> t.Type[CncGen2MapParser]:
    """Get the map parser for a game.

    Right now it basically just returns the gen 2 map parser, but we'll need this when we add SAGE support.

    :param game:
        The game the user is uploading a map for.
    :return:
        The class to use to parse a map file.
    :raises e.GameNotSupportedError:
        Raised when we don't have a parser for this game.
    """

    # We can switch to storing the base game as a field if we ever get performance issues here.
    # Uploads will be fairly rare, and this will be three queries at most though, so I am leaving it for now.
    while game.parent_game_id is not None:
        game = game.parent_game

    if (
        game.slug in GameEngines.westwood_gen_1
        or game.slug in GameEngines.westwood_gen_2
    ):
        return CncGen2MapParser

    raise e.GameNotSupportedError(game.full_name)
