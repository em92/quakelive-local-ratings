UPDATE scoreboards SET history_rating = NULL;
UPDATE matches SET post_processed = FALSE;
UPDATE gametype_ratings SET rating = NULL, n = 0;

