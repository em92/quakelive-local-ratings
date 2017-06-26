ALTER TABLE gametype_ratings DROP COLUMN rating;
ALTER TABLE scoreboards DROP COLUMN match_rating;
ALTER TABLE scoreboards DROP COLUMN old_rating;
ALTER TABLE scoreboards DROP COLUMN new_rating;

ALTER TABLE gametype_ratings ADD COLUMN mean REAL;
ALTER TABLE gametype_ratings ADD COLUMN deviation REAL;
ALTER TABLE scoreboards ADD COLUMN old_mean REAL;
ALTER TABLE scoreboards ADD COLUMN old_deviation REAL;
ALTER TABLE scoreboards ADD COLUMN new_mean REAL;
ALTER TABLE scoreboards ADD COLUMN new_deviation REAL;
