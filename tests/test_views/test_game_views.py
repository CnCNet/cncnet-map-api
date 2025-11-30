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


def test_game__cannot_be_deleted(client_god, create_cnc_game):
    """C&C games don't change much these days, so there's no real reason to expose deletions to the API.

    If you are a future person and are adding more capabilities to the game endpoints, you can just alter this test
    to use the ``client_user`` fixture to test that user's can't delete games.
    """
    my_game = create_cnc_game()

    response = client_god.delete(f"/games/{my_game.id}/", data_type=ui_objects.ResultResponseData)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_game__cannot_be_edited_by_non_admins(client_moderator, create_cnc_game):
    """C&C games don't change much so we'll only allow admins to edit them via the API.

    Maybe in the future we can allow mod authors to edit their own mod entries."""
    my_game = create_cnc_game()

    response = client_moderator.post(f"/games/{my_game.id}/", data_type=ui_objects.ResultResponseData)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_game__admins_can_edit(client_admin, create_cnc_game):
    """Admins should be able to edit a few non-structural things for games via the API."""
    my_game = create_cnc_game()
    new_full_name = f"{my_game.full_name} (Steam version)"
    new_visibility = not my_game.is_visible
    new_allow_public_uploads = not my_game.allow_public_uploads
    new_compatible_with_parent_maps = not my_game.compatible_with_parent_maps
    original_is_mod = my_game.is_mod
    original_slug = my_game.slug

    data = {
        "full_name": new_full_name,
        "is_visible": new_visibility,
        "allow_public_uploads": new_allow_public_uploads,
        "compatible_with_parent_maps": new_compatible_with_parent_maps,
        "is_mod": not original_is_mod,  # should not change, not editable via API.
        "slug": "wontwork",  # should not change, not editable via API.
    }

    response = client_admin.patch(f"/games/{my_game.id}/", data=data, data_type=ui_objects.ResultResponseData)

    assert response.status_code == status.HTTP_200_OK
    my_game.refresh_from_db()

    assert my_game.full_name == new_full_name
    assert my_game.is_visible == new_visibility
    assert my_game.allow_public_uploads == new_allow_public_uploads
    assert my_game.compatible_with_parent_maps == new_compatible_with_parent_maps
    assert my_game.is_mod == original_is_mod, "should not be changeable via the API."
    assert my_game.slug == original_slug, "should not be changeable via the API."
