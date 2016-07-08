var cfg = cat('cfg.json');
cfg = JSON.parse(cfg);
var url = cfg["db-url"].replace("mongodb://", "");
db = connect(url);
db.createCollection("matches");
db.createCollection("players");
db.createCollection("history");
quit()
