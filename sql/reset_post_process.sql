UPDATE scoreboards SET old_rating = NULL, new_rating = NULL;
UPDATE matches SET post_processed = FALSE;
UPDATE gametype_ratings SET rating = NULL, n = 0;

UPDATE gametype_ratings SET n = -999 WHERE steam_id = 76561198054367317;
