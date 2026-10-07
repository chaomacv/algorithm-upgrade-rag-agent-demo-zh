#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/password.txt" ]]; then
  set -a
  source "$SCRIPT_DIR/password.txt"
  set +a
fi
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "Set DEEPSEEK_API_KEY or add it to password.txt." >&2
  return 1 2>/dev/null || exit 1
fi
echo "DeepSeek environment loaded."
