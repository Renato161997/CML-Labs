#!/bin/bash
set -eu
test "$#" -eq 1
case "$1" in
    198.18.1.2|198.18.1.3) ;;
    *) exit 2 ;;
esac
python3 /lab/service.py --bind "$1" >/lab/service.log 2>&1 &
echo "$!" >/lab/service.pid
