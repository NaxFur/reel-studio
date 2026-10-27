#!/bin/bash
# draft.sh <proj> [step=3] [pct=35]  - quick low-res motion draft with overlay + audio -> <proj>/renders/draft.mp4
set -e
PROJ="$(cd "$1" && pwd)"; STEP="${2:-3}"; PCT="${3:-35}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
rm -rf "$PROJ/renders/draft"; mkdir -p "$PROJ/renders/draft"
"$BLENDER" -b --factory-startup "$PROJ/project/scene.blend" -P "$HERE/render_frames.py" -- "$PROJ/renders/draft" $PCT 8 --step $STEP > "$PROJ/renders/draft.log" 2>&1
cd "$PROJ/renders/draft"; i=0
for f in $(ls d_*.png | sort); do n=$(echo $f | sed 's/d_0*//;s/.png//'); for ((k=0;k<STEP;k++)); do ln -sf "$f" "seq_$(printf %05d $((n+k)))"".png"; done; done
cd "$PROJ"
ffmpeg -y -loglevel error -framerate 30 -start_number 1 -i renders/draft/seq_%05d.png -framerate 30 -i project/overlay/ov_%04d.png -i assets/audio/master.wav \
  -filter_complex "[0:v]scale=540:960[a];[1:v]scale=540:960[b];[a][b]overlay=0:0,format=yuv420p[v]" -map "[v]" -map 2:a -c:v libx264 -crf 26 -preset veryfast -c:a aac -shortest renders/draft.mp4
echo "draft: $PROJ/renders/draft.mp4"
