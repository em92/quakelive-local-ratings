import unittest

from qllr.blueprints import BalanceOptionsConvertor


class TestConvertors(unittest.TestCase):
    def test_balance_options(self):
        c = BalanceOptionsConvertor()

        self.assertEqual(c.convert("bn"), set(["bn"]))
        self.assertEqual(c.convert("bn,map_based"), set(["bn", "map_based"]))
        self.assertEqual(
            c.convert("map_based,with_qlstats_policy"),
            set(["map_based", "with_qlstats_policy"]),
        )
        with self.assertRaises(ValueError):
            c.convert("invalid")
        with self.assertRaises(ValueError):
            c.convert("with_invalid,bn")

        self.assertEqual(c.to_string(set(["bn"])), "bn")
        self.assertIn(c.to_string(set(["bn"])), ["bn"])
        self.assertIn(
            c.to_string(set(["bn", "map_based"])), ["bn,map_based", "map_based,bn"]
        )
        self.assertIn(
            c.to_string(set(["map_based", "with_qlstats_policy"])),
            ["map_based,with_qlstats_policy", "with_qlstats_policy,map_based"],
        )
