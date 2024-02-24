# Installation (on Debian Buster)

## Installing and configuring QLLR
```
# dependecies
sudo apt-get install -y
    git \
    postgresql
    python3-asgiref \
    python3-click \
    python3-cachetools \
    python3-h11 \
    python3-idna \
    python3-jinja2 \
    python3-pip \
    python3-psycopg2 \
    python3-requests \
    python3-sniffio \
    python3-typing-extensions \
    python3-venv

# install qllr
git clone https://github.com/em92/quakelive-local-ratings
cd ./quakelive-local-ratings

# create virtual environment
python3 -m venv venv
source venv/bin/activate

# install other dependencies
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

By default it is running on port 8000 and uses 127.0.0.1 as host.


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

Edit cfg.json:

- `feeder.xonstatSubmissionUrl` value must point to our qllr (example http://127.0.0.1:8000/stats/submit).
- `webadmin.urlprefix` value to `/feeder`

Now run in separate screen.
```
node feeder.node.js
```

It will run on 8081 port by default. Visit http://127.0.0.1:8081/feeder and add your quake live server(s) there.


## Installing and configuring nginx

```
sudo apt-get install nginx apache2-utils
sudo cp nginx.example.conf /etc/nginx/sites-available/stats
sudo ln -s /etc/nginx/sites-available/stats /etc/nginx/sites-enabled/stats
# edit /etc/nginx/sites-available/stats
# When copying from nginx.example.conf
# 1. domain name
# 2. path to static directory

# generate password to access /feeder via nginx
# user is admin
# password should be inputed
sudo htpasswd -c /etc/nginx/qllr.htpasswd admin

# make sure everything is fine with nginx config
sudo nginx -t

# if yes, reload nginx
sudo service nginx reload
```
