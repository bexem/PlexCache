#!/bin/bash
output=""
for d in /mnt/disk[1-9]*; do
   if [[ -e "$d$(printf "$1" | sed 's/\/mnt\/user//')" ]]; then
      output=$(dirname "$d$(printf "$1" | sed 's/\/mnt\/user//')")
      break
   fi
done

if [[ -z "$output" ]]; then
   echo "$output" #"/mnt/cache$(basename $1)"
else
   echo "$output"
fi
