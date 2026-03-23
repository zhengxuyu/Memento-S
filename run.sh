#!/usr/bin/env bash
# Launch arc_player agent for ls20 game
# Usage: ./run.sh [--model MODEL] [extra args...]
#
# Examples:
#   ./run.sh                          # default: gemini-3.1-pro-preview, shortcut, verbose
#   ./run.sh --model qwen/qwen3.5-397b-a17b
#   ./run.sh --card-id EXISTING_CARD_ID

set -euo pipefail
cd "$(dirname "$0")"

python -m arc_player \
    -g ls20 \
    --shortcut \
    -v \
    --model "${ARC_AGI_MODEL:-google/gemini-3.1-pro-preview}" \
    "$@"
