#!/bin/bash
# pipeline.sh <proj> [--say] [stills|draft|final]
#   build (always): timeline -> textures -> screens -> overlay -> audio -> master -> Blender scene
#   stills: + contact sheet at beat ends (default)   draft: + low-res motion draft   final: + full render, B variant, cover, QA
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; S="$HERE/engine/scripts"
PROJ="$(cd "$1" && pwd)"; shift
PY="${DUO_PYTHON:-$HOME/.venvs/duo-reel/bin/python}"
export BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
SAY=""; MODE="stills"
for a in "$@"; do case "$a" in --say) SAY="--say";; stills|draft|final|build) MODE="$a";; esac; done
mkdir -p "$PROJ/renders"
"$PY" "$S/build_timeline.py" "$PROJ" $SAY | tail -30
"$PY" "$S/make_textures.py" "$PROJ"
"$PY" "$S/make_screens.py" "$PROJ"
"$PY" "$S/make_overlay.py" "$PROJ"
"$PY" "$S/make_audio.py" "$PROJ"
"$PY" "$S/master_audio.py" "$PROJ" | tail -1
"$BLENDER" -b --factory-startup -P "$HERE/engine/scene/build_scene.py" -- "$PROJ" > "$PROJ/renders/build.log" 2>&1 || { tail -30 "$PROJ/renders/build.log"; exit 1; }
grep -E "ANIMATED|SAVED|Error|Traceback" "$PROJ/renders/build.log" | tail -5
case "$MODE" in
  stills) "$PY" "$S/stills.py" "$PROJ" ;;
  draft)  "$S/draft.sh" "$PROJ" ;;
  final)
    "$S/render_final.sh" "$PROJ"
    if python3 -c "import json,sys;sys.exit(0 if json.load(open('$PROJ/storyboard.json'))['meta']['hook'].get('variant_b') else 1)"; then
      "$PY" "$S/make_overlay.py" "$PROJ" --variant B && "$S/encode.sh" "$PROJ" project/overlay_b final_b.mp4
    fi
    "$BLENDER" -b --factory-startup "$PROJ/project/scene.blend" -P "$S/make_cover.py" -- "$PROJ" > "$PROJ/renders/cover.log" 2>&1
    "$PY" "$S/cover_title.py" "$PROJ"
    "$PY" "$S/qa.py" "$PROJ" ;;
esac
