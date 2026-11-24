#!/bin/sh
set -eu
: "${CTF_FLAG_03:?CTF_FLAG_03 is required}"
if [ "$(printf '%s' "$CTF_FLAG_03" | wc -l)" -ne 0 ] ||
   ! printf '%s' "$CTF_FLAG_03" | grep -Eq '^HKL\{[^{}[:cntrl:]]+\}$'; then
  echo 'CTF_FLAG_03 must have the form HKL{...}' >&2
  exit 1
fi
printf '%s' "$CTF_FLAG_03" > /flag.txt
chmod 0444 /flag.txt
unset CTF_FLAG_03
exec "$@"
