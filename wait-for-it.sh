#!/bin/sh

set -e

host="$1"
shift
cmd="$@"

while ! nc -z db 5432 -w 1; do
sleep 1;
done;

exec $cmd


