#!/usr/bin/env bash
set -euo pipefail

echo "[custom-demo] provider=mock planner=evidence"
python -m pytest -q
python -m algo_rag_demo.cli run-custom \
  --case-dir examples/custom_data/cases \
  --task-file examples/custom_data/task.txt \
  --repository-facts examples/custom_data/repository_facts.txt \
  --provider mock \
  --planner evidence \
  --top-k 3
