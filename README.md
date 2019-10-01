[![Build status](https://travis-ci.org/em92/quakelive-local-ratings.svg?branch=develop)](https://travis-ci.org/em92/quakelive-local-ratings)
[![Coverage](https://codecov.io/gh/em92/quakelive-local-ratings/branch/develop/graph/badge.svg)](https://codecov.io/gh/em92/quakelive-local-ratings)

# quakelive-local-ratings (qllr)

QLLR is webservice that:

- stores match results
- generates player's ratings
- gives API to be used in [minqlx](https://github.com/MinoMino/minqlx) with [balance](https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py) plugin to give **balanced teams**

Usually it is used with [feeder](https://github.com/em92/qlstats-feeder-mini) based on [Predath0r's](https://github.com/PredatH0r) [QLStats feeder](https://github.com/PredatH0r/XonStat/feeder) in order to collect match data from online quake live servers.

### Supported gametypes

* Attack & Defend
* Capture The Flag
* Clan Arena
* Freeze Tag
* Team Deathmatch
* Team Deathmatch (2v2)

### Differences between QLLR and [QLStats](http://qlstats.net/)

* supports TrueSkill-based rating and average player performance based rating (TODO: note in configuration)
* player ratings per map support (see [docs](docs/minqlx_config.md#map-based-ratings))
* limited supported gametypes
* [GDPR](http://eur-lex.europa.eu/eli/reg/2016/679/oj) incompatible

### Requirements

For qllr itself:

* Python 3.5 with pip
* PostgreSQL 9.5

For feeder:

* Node.js 0.11.13
* libzmq3

### Docs

* [Installation (on Debian Stretch)](docs/install.md)
* [Backing up database](docs/backup.md)
* [qlds/minqlx configuration](docs/minqlx_config.md)

### Note to European A&D and #qlpickup.ru communities

Backups of database and feeder config are [here](https://yadi.sk/d/uTqMDxzb3JPpiJ)
