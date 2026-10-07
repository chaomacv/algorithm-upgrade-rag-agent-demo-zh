#!/usr/bin/env bash
set -euo pipefail

echo "[pipeline] offline smoke test: mock embedding + evidence planner"
python -m pytest -q
python -m algo_rag_demo.cli --config configs/deepseek_bge_m3.json run \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt \
  --embedding-provider mock \
  --offline
