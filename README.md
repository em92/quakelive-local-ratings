# pickup-rating

### Requirements

* Node.js 4.3.1
* MongoDB 3.2

Maybe it can run in older versions, but I don't know. 

### Installation

* edit cfg.json to change "db-url" key to your link to your mongodb (or leave it as default);
* run following commands in shell:

```
git clone https://github.com/em92/pickup-rating.git
cd ./pickup-rating
npm update
mongo --nodb --quiet --shell "mongo_configure.js"
```

That's it. Now run

```
node main.js
```
