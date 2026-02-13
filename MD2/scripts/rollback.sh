#!/usr/bin/env bash
set -euo pipefail

if [[ "${#}" -lt 1 ]]; then
  echo "usage: rollback.sh version=vX.Y.Z" >&2
  exit 2
fi

arg="$1"
if [[ "${arg}" != version=* ]]; then
  echo "usage: rollback.sh version=vX.Y.Z" >&2
  exit 2
fi

version="${arg#version=}"

OPENCLAW_CODE_DIR="${OPENCLAW_CODE_DIR:-/opt/openclaw-x/MD2/code}"
export PYTHONPATH="${PYTHONPATH:-${OPENCLAW_CODE_DIR}}"

python3 -m core.config.rollback "${version}"

