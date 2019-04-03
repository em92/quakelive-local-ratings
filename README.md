# quakelive-local-ratings (qllr)

QLLR is quake live match stats database that can be used to generate ratings for players.
Usually it is used with [feeder](https://github.com/em92/qlstats-feeder-mini) based on [Predath0r's](https://github.com/PredatH0r) [QLStats feeder](https://github.com/PredatH0r/XonStat/feeder) in order to collect match data from online quake live servers.
On quake live server side with minqlx [balance.py](https://github.com/MinoMino/minqlx-plugins/blob/master/balance.py) plugin it can be used to generate balanced teams.

### Supported gametypes

* Attack & Defend
* Capture The Flag
* Clan Arena
* Freeze Tag
* Team Deathmatch
* Team Deathmatch (2v2)

### Differences between QLLR and [QLStats](http://qlstats.net/)

* common player ratings support (based on TrueSkill or optinonally average player performance)
* player ratings per map support (based on average player perfomance)
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
