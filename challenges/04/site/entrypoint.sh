#!/bin/sh
set -eu
: "${CTF_FLAG_04:?CTF_FLAG_04 is required}"
if [ "$(printf '%s' "$CTF_FLAG_04" | wc -l)" -ne 0 ] ||
   ! printf '%s' "$CTF_FLAG_04" | grep -Eq '^HKL\{[^{}[:cntrl:]]+\}$'; then
  echo 'CTF_FLAG_04 must have the form HKL{...}' >&2
  exit 1
fi
printf '%s' "$CTF_FLAG_04" > /app/flag.txt
chmod 0444 /app/flag.txt
unset CTF_FLAG_04
exec "$@"
