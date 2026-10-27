#!/bin/bash
# install.sh - check the tools reel-studio needs, create its Python environment and link the skill
# into Claude Code. Safe to re-run. Downloads nothing unless you pass --model.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${DUO_PYTHON_VENV:-$HOME/.venvs/duo-reel}"
MODEL="${WHISPER_MODEL:-$HOME/whisper-models/ggml-medium.en.bin}"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
ok() { printf "  \033[32mok\033[0m  %s\n" "$1"; }
no() { printf "  \033[31m--\033[0m  %s\n" "$1"; MISSING=1; }

echo "Checking tools"
[ -x "$BLENDER" ] && ok "Blender: $("$BLENDER" --version 2>/dev/null | head -1)" || no "Blender 5.x not found at \$BLENDER ($BLENDER) - https://www.blender.org/download/"
command -v ffmpeg >/dev/null && ok "ffmpeg" || no "ffmpeg (macOS: brew install ffmpeg)"
command -v whisper-cli >/dev/null && ok "whisper-cli" || no "whisper-cli (macOS: brew install whisper-cpp)"
command -v say >/dev/null && ok "say (free draft voices)" || echo "  ..  no 'say': skip --say drafts and use real takes"
command -v python3 >/dev/null && ok "python3" || no "python3"

echo "Python environment: $VENV"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet -r "$ROOT/setup/requirements.txt" && ok "numpy, scipy, soundfile, pillow"

echo "Whisper model: $MODEL"
if [ -f "$MODEL" ]; then ok "found"
elif [ "$1" = "--model" ]; then
  mkdir -p "$(dirname "$MODEL")"
  curl -L --fail -o "$MODEL" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin && ok "downloaded"
else no "missing - re-run with --model to download ggml-medium.en.bin (about 1.5 GB), or set WHISPER_MODEL"; fi

echo "Claude Code skill"
mkdir -p "$HOME/.claude/skills"
if [ -e "$HOME/.claude/skills/duo-sketch-reel" ] && [ ! -L "$HOME/.claude/skills/duo-sketch-reel" ]; then
  no "~/.claude/skills/duo-sketch-reel already exists and is not a link: left it alone"
else ln -sfn "$ROOT/skills/duo-sketch-reel" "$HOME/.claude/skills/duo-sketch-reel" && ok "linked ~/.claude/skills/duo-sketch-reel"; fi

[ -z "$MISSING" ] && echo "Ready. Try: skills/duo-sketch-reel/pipeline.sh examples/env-rotate --say stills" || echo "Fix the -- lines above, then re-run."
