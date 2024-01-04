from kirovy.models import CncGame
from kirovy.services.cnc_gen_2_services import CncGen2MapParser


def get_parser_for_game(game_id: str) -> CncGen2MapParser:
    game = CncGame.objects.get(id=game_id)
