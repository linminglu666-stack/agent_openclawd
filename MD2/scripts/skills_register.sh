#!/usr/bin/env bash
set -euo pipefail

MD2_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODE_DIR="${MD2_DIR}/code"
SKILLS_DIR="${MD2_DIR}/skills"
REGISTRY_PATH="${SKILLS_DIR}/registry.json"

python3 "${MD2_DIR}/scripts/skills_validate.py"

export PYTHONPATH="${CODE_DIR}"
python3 - <<PY
from core.skills.registry import SkillsRegistry

reg = SkillsRegistry.build_from_dir("${SKILLS_DIR}")
reg.save("${REGISTRY_PATH}")
print("${REGISTRY_PATH}")
PY

