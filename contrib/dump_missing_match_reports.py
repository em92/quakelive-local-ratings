#!/usr/bin/env python3

from os.path import isfile

from dump_qlstats_data import download_stats

from qllr.db import db_connect


def main(args):
    try:
        path = args[1]
        if path.endswith("/") == False:
            path += "/"
    except IndexError:
        path = "./"

    db = db_connect()

    cu = db.cursor()
    cu.execute("SELECT match_id, timestamp FROM matches")
    for row in cu.fetchall():
        if isfile(path + row[0] + ".json.gz") == False:
            download_stats(row[0], row[1], path)
    db.close()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
