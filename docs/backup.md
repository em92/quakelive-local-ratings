# Backing up database

## Export database

```
python3 -m contrib.dump_backup
```

It will generate .tar.gz file as database backup.

## Import database

```
python3 -m contrib.restore_backup filename.tar.gz
```