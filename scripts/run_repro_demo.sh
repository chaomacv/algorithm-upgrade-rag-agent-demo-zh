#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROVIDER="${1:-mock}"
PLANNER="${2:-mock}"

if [[ "$PLANNER" == "deepseek" && -f "./load_deepseek_env.sh" ]]; then
  # The file is intentionally gitignored because it loads local API credentials.
  source ./load_deepseek_env.sh
fi

if [[ "$PROVIDER" == "bge-m3" ]]; then
  export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
  export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
fi

echo "[repro-demo] provider=$PROVIDER planner=$PLANNER"
echo "[repro-demo] running tests"
python -m pytest -q

echo "[repro-demo] rebuilding index"
python -m algo_rag_demo.cli build-index --provider "$PROVIDER"

echo "[repro-demo] running failure-recovery loop"
python -m algo_rag_demo.cli demo-failure --provider "$PROVIDER" --planner "$PLANNER"
