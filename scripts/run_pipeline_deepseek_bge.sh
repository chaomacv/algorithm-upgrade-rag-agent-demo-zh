#!/usr/bin/env bash
set -euo pipefail
# Compatibility entrypoint for existing users.
bash "$(dirname "${BASH_SOURCE[0]}")/run_demo.sh" "$@"
