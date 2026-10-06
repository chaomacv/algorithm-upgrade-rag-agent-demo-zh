#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "./load_deepseek_env.sh" ]]; then
  # The file is intentionally gitignored because it loads local API credentials.
  source ./load_deepseek_env.sh
fi

export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"

echo "[live-demo] provider=bge-m3 planner=deepseek"
echo "[live-demo] running tests"
python -m pytest -q

echo "[live-demo] rebuilding BGE-M3 index"
python -m algo_rag_demo.cli build-index --provider bge-m3

echo "[live-demo] running live failure-recovery scenario"
python -m algo_rag_demo.cli demo-failure --provider bge-m3 --planner deepseek
