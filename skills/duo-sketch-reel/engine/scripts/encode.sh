#!/bin/bash
# encode.sh <proj> [overlay_dir] [output]  - 3D frames + overlay + master audio -> H.264/AAC 1080x1920
set -e
PROJ="$(cd "$1" && pwd)"; cd "$PROJ"
OV="${2:-project/overlay}"; OUT="${3:-final.mp4}"
NF=$(python3 -c "import json;print(json.load(open('project/timeline.json'))['frames'])")
DUR=$(python3 -c "import json;print(json.load(open('project/timeline.json'))['frames']/30)")
ffmpeg -y -loglevel error -framerate 30 -i renders/final/frame_%04d.png -framerate 30 -i "$OV/ov_%04d.png" -i assets/audio/master.wav \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]" -map "[v]" -map 2:a \
  -c:v libx264 -profile:v high -level 4.2 -preset slow -crf 17 -g 60 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 256k -ar 48000 -frames:v "$NF" -t "$DUR" -movflags +faststart "$OUT"
echo "encoded $OUT ($NF frames, ${DUR}s)"
