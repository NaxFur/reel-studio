#!/bin/bash
# render_final.sh <proj> [workers=3] [samples=16]  - resumable full-res render (skips finished frames), then encode
set -e
PROJ="$(cd "$1" && pwd)"; W="${2:-3}"; SPP="${3:-16}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
KEEPAWAKE=""; command -v caffeinate >/dev/null && KEEPAWAKE="caffeinate -i"   # macOS: keep the machine awake while rendering
NF=$(python3 -c "import json;print(json.load(open('$PROJ/project/timeline.json'))['frames'])")
mkdir -p "$PROJ/renders/final"
PIDS=()
for ((i=0; i<W; i++)); do
  A=$(( i * NF / W + 1 )); B=$(( (i + 1) * NF / W ))
  $KEEPAWAKE "$BLENDER" -b --factory-startup "$PROJ/project/scene.blend" -P "$HERE/render_range.py" -- "$PROJ/renders/final" $A $B $SPP > "$PROJ/renders/render_w$i.log" 2>&1 &
  PIDS+=($!)
done
wait "${PIDS[@]}"
N=$(ls "$PROJ/renders/final" | grep -c frame_)
[ "$N" -ge "$NF" ] || { echo "only $N/$NF frames rendered"; exit 1; }
"$HERE/encode.sh" "$PROJ"
