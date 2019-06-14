import unittest

from qllr.db import cache, rating_column


class TestCache(unittest.TestCase):
    def _test_lengths(self, a, b):
        len1 = len(a)
        len2 = len(b)
        self.assertNotEqual(len1, 0)
        self.assertNotEqual(len2, 0)
        self.assertEqual(len1, len2)

    def test_medals(self):
        self._test_lengths(cache.MEDALS_AVAILABLE, cache.MEDAL_IDS)

    def test_weapons(self):
        self._test_lengths(cache.WEAPONS_AVAILABLE, cache.WEAPON_IDS)

    def test_gametypes(self):
        self._test_lengths(cache.GAMETYPE_IDS, cache.GAMETYPE_NAMES)
        set1 = set(cache.GAMETYPE_IDS.keys())
        set2 = set(cache.GAMETYPE_NAMES.keys())
        self.assertEqual(set1, set2)

    def test_rating_column_avg_perf(self):
        self.assertEqual(rating_column("tdm"), "r2_value")

    def test_rating_column_avg_trueskill(self):
        self.assertEqual(rating_column("ad"), "r1_mean")
