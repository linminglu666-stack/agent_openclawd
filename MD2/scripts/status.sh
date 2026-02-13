#!/usr/bin/env bash
set -euo pipefail

units=(
  openclawd-scheduler.service
  openclawd-orchestrator.service
  openclawd-runner.service
  openclawd-memory-indexer.service
  openclawd-eval.service
  openclawd-bff.service
)

for unit in "${units[@]}"; do
  systemctl --no-pager status "${unit}" || true
done

