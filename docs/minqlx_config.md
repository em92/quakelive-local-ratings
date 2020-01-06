# qlds/minqlx configuration

## Common ratings
In server.cfg:

```
seta qlx_balanceUrl "YOUR-HOST-HERE"
seta qlx_balanceMinimumSuggestionDiff 0
seta qlx_balanceApi "elo"
```

Make sure that http://YOUR-HOST-HERE/elo/666 is accessible.

## Map-based ratings

Make sure that you are using [latest balance.py plugin](https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py) and in server.cfg:

```
seta qlx_balanceApi "elo/map_based"
```

## Bigger rating values

Sometimes it is more convenient for players in-game to have 1500 rating instead of 25. For that you need to set in server.cfg:

```
seta qlx_balanceApi "elo/bn"
```

## QLStats privacy policy

If you want use [qlstats_privacy_policy plugin](https://github.com/mgaertne/minqlx-plugin-tests/blob/master/src/main/python/qlstats_privacy_policy.py)
you need to set in server.cfg:

```
seta qlx_balanceApi "elo/with_qlstats_policy"
```

## Combinations of above

```
seta qlx_balanceApi "elo/bn,map_based"  // enables map_based rating and ratings values are bigger
seta qlx_balanceApi "elo/bn,with_qlstats_policy" // ratings values are bigger and returns privacy policy data from qlstats.net
seta qlx_balanceApi "elo/map_based,bn,with_qlstats_policy" // all in one

```
