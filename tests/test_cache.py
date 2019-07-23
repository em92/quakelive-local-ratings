from qllr.db import cache, rating_column
from qllr.templating import templates


def _test_lengths(a, b):
    len1 = len(a)
    len2 = len(b)
    assert len1 != 0
    assert len2 != 0
    assert len1 == len2


def test_medals():
    _test_lengths(cache.MEDALS_AVAILABLE, cache.MEDAL_IDS)


def test_weapons():
    _test_lengths(cache.WEAPONS_AVAILABLE, cache.WEAPON_IDS)


def test_gametypes():
    _test_lengths(cache.GAMETYPE_IDS, cache.GAMETYPE_NAMES)
    set1 = set(cache.GAMETYPE_IDS.keys())
    set2 = set(cache.GAMETYPE_NAMES.keys())
    assert set1 == set2


def test_rating_column_avg_perf():
    assert rating_column("tdm") == "r2_value"


def test_rating_column_avg_trueskill():
    assert rating_column("ad") == "r1_mean"


def test_ensure_gametype_names_in_template_globals():
    assert templates.env.globals["gametype_names"] == cache.GAMETYPE_NAMES
