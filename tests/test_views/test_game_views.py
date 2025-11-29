from rest_framework import status

from kirovy.objects import ui_objects
from kirovy.models import CncGame


def test_game_detail(client_anonymous, game_yuri):
    """Test the game details."""
    response = client_anonymous.get(f"/games/{game_yuri.id}/", data_type=ui_objects.ResultResponseData)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["result"]["id"] == str(game_yuri.id)
    assert response.data["result"]["slug"] == game_yuri.slug
    assert response.data["result"]["full_name"] == game_yuri.full_name
    assert response.data["result"]["is_visible"] == game_yuri.is_visible
    assert response.data["result"]["is_mod"] == game_yuri.is_mod
    assert response.data["result"]["allow_public_uploads"] == game_yuri.allow_public_uploads
    assert response.data["result"]["compatible_with_parent_maps"] == game_yuri.compatible_with_parent_maps
    assert response.data["result"]["parent_game_id"] == str(game_yuri.parent_game_id)
    assert set(response.data["result"]["allowed_extension_ids"]) == {
        str(ae.id) for ae in game_yuri.allowed_extensions.select_related()
    }


def test_game_list_user(client_user, create_cnc_game):
    """Test that users can see all visible games."""
    invisible = create_cnc_game(is_visible=False)
    all_games = CncGame.objects.filter(is_visible=True)
    expected = {str(g.id): g for g in all_games}
    assert str(invisible.id) not in expected.keys()

    response = client_user.get("/games/", data_type=ui_objects.ListResponseData)

    assert response.status_code == status.HTTP_200_OK

    for response_game in response.data["results"]:
        expected_game = expected.get(response_game["id"])
        assert expected_game
        assert response_game["id"] == str(expected_game.id)
        assert response_game["slug"] == expected_game.slug
        assert response_game["full_name"] == expected_game.full_name
        assert response_game["is_visible"] == expected_game.is_visible
        assert response_game["is_mod"] == expected_game.is_mod
        assert response_game["allow_public_uploads"] == expected_game.allow_public_uploads
        assert response_game["compatible_with_parent_maps"] == expected_game.compatible_with_parent_maps
        if expected_game.parent_game_id:
            assert response_game["parent_game_id"] == str(expected_game.parent_game_id)
        assert set(response_game["allowed_extension_ids"]) == {
            str(ae.id) for ae in expected_game.allowed_extensions.select_related()
        }


def test_game__hidden_games_visible_to_moderators(client_moderator, create_cnc_game):
    """Test that hidden games are visible to moderators."""
    invisible = create_cnc_game(is_visible=False)

    response = client_moderator.get("/games/", data_type=ui_objects.ListResponseData)
    assert response.status_code == status.HTTP_200_OK

    assert str(invisible.id) in [r["id"] for r in response.data["results"]]
