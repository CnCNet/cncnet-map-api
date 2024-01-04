import enum

from django.utils.translation import gettext as _

cnc_prefix = _("Command & Conquer:")

cncnet_token_url = "https://ladder.cncnet.org/api/v1/auth/token"
cncnet_user_url = "https://ladder.cncnet.org/api/v1/user/info"


class GameSlugs(enum.StrEnum):
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
    dune_2000 = "d2k"
    generals = "gen"
    zero_hour = "zh"
    battle_for_middle_earth = "bfme"
    battle_for_middle_earth_2 = "bfme2"
    tiberium_wars = "tw"
    kanes_wrath = "kw"
    red_alert_3 = "ra3"
    red_alert_3_uprising = "ra3u"


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
