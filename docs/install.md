# Installation (on Debian Buster)

## Installing and configuring QLLR
```
# base apps
sudo apt-get install python3 python3-pip postgresql git

# psycopg2 build prerequires
sudo apt-get install python3-dev libpq-dev gcc

# install qllr
git clone https://github.com/em92/quakelive-local-ratings
cd ./quakelive-local-ratings
python3 -m pip install -r requirements.txt
```

All config is in `.env` file. See `.env.example`.


Assuming that we are making database "qllr" with owner's name "eugene" and password "bebebe".
If not - edit `.env` file to change `DATABASE_URL` value.

* creating database in postgresql

```
sudo -u postgres psql
```

in postgresql shell:
```
CREATE DATABASE qllr;
CREATE USER eugene WITH password 'bebebe';
ALTER DATABASE qllr OWNER TO eugene;
\q
```

* deploying database (if you have database backup to restore - ignore this step and do [this](backup.md) instead)
```
psql -h localhost qllr eugene
```

in postgresql shell:
```
\i sql/init.sql
\q
```

That's it. Now run in separate screen.

```
./main.py
```

By default it is running on port 8000.


## Installing and configuring feeder

```
git clone https://github.com/em92/qlstats-feeder-mini.git
sudo apt-get install nodejs
sudo ln -s /usr/bin/nodejs /usr/bin/node
sudo apt-get install npm
sudo apt-get install libzmq3-dev
mv qlstats-feeder-mini feeder
cd feeder
npm install
mkdir ql-match-jsons
mkdir ql-match-jsons/errors
```

Edit cfg.json. *xonstatSubmissionUrl* value must point to our qllr (example http://YOUR-HOST-HERE:8000/stats/submit).

Now run in separate screen.
```
node feeder.node.js
```

It will run on 8081 port by default. Visit http://YOUR-HOST-HERE:8081 and add your quake live server(s) there.
