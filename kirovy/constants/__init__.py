import enum
from kirovy import typing as t

from django.utils.translation import gettext as _

CNC_PREFIX = _("Command & Conquer:")

CNCNET_TOKEN_URL = "https://ladder.cncnet.org/api/v1/auth/token"
CNCNET_USER_URL = "https://ladder.cncnet.org/api/v1/user/info"

CNCNET_INI_SECTION = "CnCNet"
CNCNET_INI_MAP_ID_KEY = "ID"
CNCNET_INI_MAP_PARENT_ID_KEY = "ParentID"


class CncnetUserGroup:
    """A class with the user roles in the CnCNet Ladder API, and helpers for roles."""

    USER: t.Literal["User"] = "User"
    MOD: t.Literal["Moderator"] = "Moderator"
    ADMIN: t.Literal["Admin"] = "Admin"
    GOD: t.Literal["God"] = "God"
    KANE: t.Literal["God"] = GOD

    STAFF_ROLES: t.Set[t.LiteralString] = {MOD, ADMIN, GOD}
    ADMIN_ROLES: t.Set[t.LiteralString] = {ADMIN, GOD}

    RoleType = t.Union[
        t.Type[USER],
        t.Type[MOD],
        t.Type[ADMIN],
        t.Type[GOD],
    ]

    @staticmethod
    def normalize_group_string_case(user_group: str) -> str:
        """Normalize the case in a user group from the API.

        This is here just in case a role without the correct capitalization sneaks
        in. We want role checks to work regardless.

        :param user_group:
            A user group string from the ladder API.
        :return:
            The same string with the correct case, e.g. "user" becomes "User".
        """
        return user_group.lower().capitalize()

    @classmethod
    def is_staff(cls, user_group: str) -> bool:
        """Check if a user group string is staff.

        :param user_group:
            The user group string from cncnet. This function
            can handle inconsistent case, but roles from the Ladder API should be
            capitalized, e.g. "User".
        :return:
            True if the user is staff or admin.
        """
        user_group = cls.normalize_group_string_case(user_group)
        return user_group in cls.STAFF_ROLES or cls.is_admin(user_group)

    @classmethod
    def is_admin(cls, user_group: str) -> bool:
        """Check if a user group string is admin.

        :param user_group:
            The user group string from cncnet. This function
            can handle inconsistent case, but roles from the Ladder API should be
            capitalized, e.g. "User".
        :return:
            True if the user is admin.
        """
        user_group = cls.normalize_group_string_case(user_group)
        return user_group in cls.ADMIN_ROLES

    @classmethod
    def is_messiah(cls, user_group: str) -> bool:
        """Check if a user group string is Kane, the Messiah.

        :param user_group:
            The user group string from cncnet. This function
            can handle inconsistent case, but roles from the Ladder API should be
            capitalized, e.g. "User".
        :return:
            True if the user is Kane, the Messiah.
        """
        user_group = cls.normalize_group_string_case(user_group)
        return user_group == cls.KANE


class MigrationUser:
    CNCNET_ID = -1
    USERNAME = "MobileConstructionVehicle_Migrator"
    GROUP = CncnetUserGroup.USER


class LegacyUploadUser:
    CNCNET_ID = -2
    USERNAME = "Spy_ShapeShifting_LegacyUploader"
    GROUP = CncnetUserGroup.USER


class GameSlugs(str, enum.Enum):
    """The slugs for each game / total conversion mod.

    These **must** be unique. They are in constants because we need them to determine which parser to use
    for maps and collections.

    ## IF YOU CHANGE THESE THEN YOU **MUST** MAKE A DATA MIGRATION!!!

    DO NOT forget the fucking [data-migration](https://docs.djangoproject.com/en/4.2/topics/migrations/#data-migrations)
    or Yuri will save a spot for you in a grinder.

    Seriously, you will brick the site and require a rollback.
    """

    tiberian_dawn = "td"
    red_alert = "ra"
    tiberian_sun = "ts"
    dawn_of_the_tiberium_age = "dta"
    red_alert_2 = "ra2"
    yuris_revenge = "yr"
    mental_omega = "mo"
    cnc_reloaded = "cncr"
    rise_of_the_east = "rote"
    red_resurrection = "rr"
    dune_2000 = "d2"
    generals = "gen"
    zero_hour = "zh"
    battle_for_middle_earth = "bfme"
    battle_for_middle_earth_2 = "bfme2"
    tiberium_wars = "tw"
    kanes_wrath = "kw"
    red_alert_3 = "ra3"
    red_alert_3_uprising = "ra3u"


BACKWARDS_COMPATIBLE_GAMES = [
    GameSlugs.tiberian_dawn,
    GameSlugs.red_alert,
    GameSlugs.tiberian_sun,
    GameSlugs.dawn_of_the_tiberium_age,
    GameSlugs.yuris_revenge,
    GameSlugs.dune_2000,
]
"""attr: These are the games that MapDB 1.0 supported.
We need to maintain backwards compatibility for clients we can't update.
"""


class GameEngines:
    """Maps the game slugs to the general game engine.

    Exists to determine which parsers to use for which uploaded files based on ``object.game.slug``

    Only include top-level parents because total-conversions and expansions will use the same engine as the base game.
    """

    westwood_gen_1 = {GameSlugs.tiberian_dawn, GameSlugs.red_alert}
    westwood_gen_2 = {GameSlugs.tiberian_sun, GameSlugs.red_alert_2}
    sage_gen_1 = {
        GameSlugs.generals,
        GameSlugs.battle_for_middle_earth,
        GameSlugs.battle_for_middle_earth_2,
    }
    sage_gen_2 = {GameSlugs.tiberium_wars, GameSlugs.red_alert_3}
