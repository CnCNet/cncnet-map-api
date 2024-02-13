import pytest

from kirovy.constants import CncnetUserGroup


def test_cnc_user_groups():
    """Test the user role checking."""
    assert not CncnetUserGroup.is_staff(CncnetUserGroup.USER)
    assert CncnetUserGroup.is_staff(CncnetUserGroup.MOD)
    assert CncnetUserGroup.is_staff(CncnetUserGroup.ADMIN)
    assert CncnetUserGroup.is_staff(CncnetUserGroup.GOD)
    assert CncnetUserGroup.is_staff(CncnetUserGroup.KANE)

    assert not CncnetUserGroup.is_admin(CncnetUserGroup.USER)
    assert not CncnetUserGroup.is_admin(CncnetUserGroup.MOD)
    assert CncnetUserGroup.is_admin(CncnetUserGroup.ADMIN)
    assert CncnetUserGroup.is_admin(CncnetUserGroup.GOD)
    assert CncnetUserGroup.is_admin(CncnetUserGroup.KANE)

    assert not CncnetUserGroup.is_messiah(CncnetUserGroup.USER)
    assert not CncnetUserGroup.is_messiah(CncnetUserGroup.MOD)
    assert not CncnetUserGroup.is_messiah(CncnetUserGroup.ADMIN)
    assert CncnetUserGroup.is_messiah(CncnetUserGroup.GOD)
    assert CncnetUserGroup.is_messiah(CncnetUserGroup.KANE)


@pytest.mark.parametrize("user_group", ["admin", "aDmin", "gOd", "ADMIN"])
def test_cnc_user_groups__bad_case(user_group: str):
    """Test that we can handle weird casing during user group checks."""
    assert CncnetUserGroup.is_admin(user_group)
