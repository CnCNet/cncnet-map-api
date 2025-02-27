from django import urls
from rest_framework import status

BASE_URL = "/maps/delete/"


def test_delete_own_map(client_user, create_cnc_map):
    """Right now, only staff can delete maps."""
    cnc_map = create_cnc_map(user_id=client_user.kirovy_user.id)

    url = f"{BASE_URL}{cnc_map.id}/"

    response = client_user.delete(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_map__staff(client_moderator, create_cnc_map, user):
    """Moderators should be able to delete maps."""
    cnc_map = create_cnc_map(user_id=user.id)
    url = f"{BASE_URL}{cnc_map.id}/"

    response = client_moderator.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_map__legacy(client_god, create_cnc_map):
    """No one can delete maps over the API."""
    cnc_map = create_cnc_map(user_id=None, is_legacy=True)
    url = f"{BASE_URL}{cnc_map.id}/"

    response = client_god.delete(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
