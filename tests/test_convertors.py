from pytest import raises

from qllr.blueprints import BalanceOptionsConvertor


def test_balance_options():
    c = BalanceOptionsConvertor()

    assert c.convert("bn") == set(["bn"])
    assert c.convert("bn,map_based") == set(["bn", "map_based"])
    assert c.convert("map_based,with_qlstats_policy") == set(
        ["map_based", "with_qlstats_policy"]
    )
    with raises(ValueError):
        c.convert("invalid")
    with raises(ValueError):
        c.convert("with_invalid,bn")

    assert c.to_string(set(["bn"])) == "bn"
    assert c.to_string(set(["bn"])) in ["bn"]
    assert c.to_string(set(["bn", "map_based"])) in ["bn,map_based", "map_based,bn"]
    assert c.to_string(set(["map_based", "with_qlstats_policy"])) in [
        "map_based,with_qlstats_policy",
        "with_qlstats_policy,map_based",
    ]
