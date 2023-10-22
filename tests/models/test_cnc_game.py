from kirovy.models import CncGame


def test_cnc_game_url(db, settings):
    """Test that we generate the proper urls for logo and icon files."""
    ra2 = CncGame(full_name="Red Alert 2", slug="ra2")

    settings.STATIC_URL = "st/"
    settings.CNC_GAME_IMAGE_DIRECTORY = "gi/"
    assert ra2.icon_url == "/st/gi/ra2/ra2-icon.png"
    assert ra2.logo_url == "/st/gi/ra2/logo.png"
