### Installation on Debian Stretch

```
# base apps
sudo apt-get install python3 python3-pip postgresql git

# install qllr
git clone https://github.com/em92/quakelive-local-ratings
cd ./quakelive-local-ratings
sudo pip3 install -r requirements.txt
```

Assuming that we are making database "qllr" with owner's name "eugene" and password "bebebe".
If not - edit cfg.json to change "db_url" key.

* creating database in postgresql

```
sudo -u postgres psql
```

in postgresql shell:
```
CREATE DATABASE qllr;
CREATE USER eugene WITH password 'bebebe';
GRANT ALL ON DATABASE qllr TO eugene;
\q
```

* deploying database (if you have database backup to restore - ignore this step and do [this](README.md#import-database) instead)
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

By default it is running on port 7081.


### Installing and configurating feeder

```
git clone https://github.com/PredatH0r/XonStat.git
sudo apt-get install nodejs
sudo ln -s /usr/bin/nodejs /usr/bin/node
sudo apt-get install npm
sudo apt-get install libzmq3
sudo apt-get install libzmq3-dev
cd XonStat/feeder
npm install
mkdir ql-match-jsons
mkdir ql-match-jsons/errors
sed -i.bak '/database/d' cfg.json
```

Edit cfg.json. *xonstatSubmissionUrl* value must point to our qllr (example http://YOUR-HOST-HERE:7081/stats/submit).

Now run in separate screen.
```
node feeder.node.js
```

It will run on 8081 port by default. Visit http://YOUR-HOST-HERE:8081 and add your quake live server(s) there.
