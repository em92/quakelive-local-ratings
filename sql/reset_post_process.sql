UPDATE scoreboards SET old_r1_mean = NULL, old_r1_deviation = NULL, old_r2_value = NULL;
UPDATE scoreboards SET new_r1_mean = NULL, new_r1_deviation = NULL, new_r2_value = NULL;
UPDATE matches SET post_processed = FALSE;
UPDATE gametype_ratings SET r1_mean = NULL, r1_deviation = NULL, r2_value = NULL, n = 0;

UPDATE gametype_ratings SET n = -999 WHERE steam_id = 76561198054367317;
