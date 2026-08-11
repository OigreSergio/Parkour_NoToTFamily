#!/usr/bin/env sh
# Scarica in data/fonts/ i glifi Noto Sans usati dallo stile ricamo
# (Regular e Bold, tutti i range 0-65535) da OpenFreeMap.
set -eu
cd "$(dirname "$0")"
for font in "Noto Sans Regular" "Noto Sans Bold"; do
  enc=$(printf '%s' "$font" | sed 's/ /%20/g')
  mkdir -p "data/fonts/$font"
  start=0
  while [ "$start" -le 65280 ]; do
    end=$((start + 255))
    f="data/fonts/$font/$start-$end.pbf"
    [ -s "$f" ] || curl -sf "https://tiles.openfreemap.org/fonts/$enc/$start-$end.pbf" -o "$f" || true
    start=$((end + 1))
  done
  echo "$font: $(ls "data/fonts/$font" | wc -l) range scaricati"
done
