# quakelive-local-ratings (qllr)

QLLR is quake live match stats database that can be used to generate ratings for players.
Usually it is used with [feeder](https://github.com/PredatH0r/XonStat/tree/master/feeder) from [Predath0r's](https://github.com/PredatH0r) [QLStats](https://github.com/PredatH0r/XonStat) repository in order to collect match data from online quake live servers.
On quake live server side with minqlx [balance.py](https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py) plugin it can be used to generate balanced teams.

### Supported gametypes

* Attack & Defend
* Capture The Flag
* Team Deathmatch

### Differences between QLLR and [QLStats](http://qlstats.net/)

* common player ratings support (based on TrueSkill or optinonally average player performance)
* player ratings per map support (based on average player perfomance)
* limited supported gametypes

### Requirements

For qllr itself:
* Python 3.4 with pip
* PostgreSQL 9.5

For feeder:
* Node.js 0.11.13
* libzmq3

### Installation

* [Instructions for Debian Jessie](README-Debian-Jessie.md)
* [Instructions for Debian Stretch](README-Debian-Stretch.md)

### qlds/minqlx configuration

In server.cfg:

```
seta qlx_balanceUrl "YOUR-HOST-HERE"
seta qlx_balanceMinimumSuggestionDiff 0
seta qlx_balanceApi "elo"
```

Make sure that http://YOUR-HOST-HERE/elo/666 is accessible.

If you want to used per-map ratings, make sure that you are using [modified balance.py plugin](https://github.com/em92/minqlx-plugins/blob/master/balance.py) and in server.cfg:

```
seta qlx_balanceApi "elo_map"
```
