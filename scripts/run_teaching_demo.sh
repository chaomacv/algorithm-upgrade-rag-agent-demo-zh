#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[teaching-demo] provider=mock planner=mock"
echo "[teaching-demo] running tests"
python -m pytest -q

echo "[teaching-demo] rebuilding mock index"
python -m algo_rag_demo.cli build-index --provider mock

echo "[teaching-demo] running deterministic failure-recovery scenario"
python -m algo_rag_demo.cli demo-failure --provider mock --planner mock
