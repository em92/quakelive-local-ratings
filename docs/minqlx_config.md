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

If you want to used per-map ratings, make sure that you are using [modified balance.py plugin](https://github.com/em92/minqlx-plugins/blob/master/balance.py) and in server.cfg:

```
seta qlx_balanceApi "elo_map"
```