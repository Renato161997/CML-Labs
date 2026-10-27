#!/bin/sh
set -eu
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
# CML provisions interfaces before running the separate /boot.sh day-zero job.
sleep 1
exec /bin/bash --noprofile --norc -i
