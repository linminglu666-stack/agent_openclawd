#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "must_run_as_root" >&2
  exit 1
fi

OPENCLAW_USER="${OPENCLAW_USER:-openclaw}"
OPENCLAW_GROUP="${OPENCLAW_GROUP:-openclaw}"
OPENCLAW_INSTALL_DIR="${OPENCLAW_INSTALL_DIR:-/opt/openclaw-x}"
OPENCLAW_CODE_DIR="${OPENCLAW_CODE_DIR:-${OPENCLAW_INSTALL_DIR}/MD2/code}"
OPENCLAW_ETC_DIR="${OPENCLAW_ETC_DIR:-/etc/openclaw-x}"
OPENCLAW_ENV_FILE="${OPENCLAW_ENV_FILE:-${OPENCLAW_ETC_DIR}/openclaw-x.env}"
OPENCLAW_SYSTEMD_DIR="${OPENCLAW_SYSTEMD_DIR:-/etc/systemd/system}"
OPENCLAW_TEMPLATE_DIR="${OPENCLAW_TEMPLATE_DIR:-${OPENCLAW_INSTALL_DIR}/MD2/systemd}"

mkdir -p "${OPENCLAW_ETC_DIR}"

if [[ ! -f "${OPENCLAW_ENV_FILE}" ]]; then
  cat > "${OPENCLAW_ENV_FILE}" <<EOF
OPENCLAW_CODE_DIR=${OPENCLAW_CODE_DIR}
PYTHONPATH=${OPENCLAW_CODE_DIR}
OPENCLAW_STATE_DIR=/var/lib/openclaw-x
OPENCLAW_LOG_DIR=/var/log/openclaw-x
OPENCLAW_RUNTIME_DIR=/run/openclaw-x
EOF
fi

render_unit() {
  local template_path="$1"
  local out_path="$2"
  sed \
    -e "s|@OPENCLAW_USER@|${OPENCLAW_USER}|g" \
    -e "s|@OPENCLAW_GROUP@|${OPENCLAW_GROUP}|g" \
    -e "s|@OPENCLAW_CODE_DIR@|${OPENCLAW_CODE_DIR}|g" \
    "${template_path}" > "${out_path}"
}

install_unit_if_changed() {
  local unit_name="$1"
  local template_path="${OPENCLAW_TEMPLATE_DIR}/${unit_name}.in"
  local target_path="${OPENCLAW_SYSTEMD_DIR}/${unit_name}"

  if [[ ! -f "${template_path}" ]]; then
    echo "template_not_found:${template_path}" >&2
    exit 1
  fi

  local tmp
  tmp="$(mktemp)"
  render_unit "${template_path}" "${tmp}"

  if [[ -f "${target_path}" ]] && cmp -s "${tmp}" "${target_path}"; then
    rm -f "${tmp}"
    return 1
  fi

  install -m 0644 "${tmp}" "${target_path}"
  rm -f "${tmp}"
  return 0
}

units=(
  openclawd-scheduler.service
  openclawd-orchestrator.service
  openclawd-runner.service
  openclawd-memory-indexer.service
  openclawd-eval.service
  openclawd-bff.service
)

changed_any=0
for unit in "${units[@]}"; do
  if install_unit_if_changed "${unit}"; then
    changed_any=1
  fi
done

systemctl daemon-reload

for unit in "${units[@]}"; do
  systemctl enable "${unit}" >/dev/null
done

if [[ "${changed_any}" -eq 1 ]]; then
  for unit in "${units[@]}"; do
    systemctl restart "${unit}" || systemctl start "${unit}"
  done
else
  for unit in "${units[@]}"; do
    systemctl start "${unit}" || true
  done
fi

for unit in "${units[@]}"; do
  systemctl is-active --quiet "${unit}" || echo "not_active:${unit}" >&2
done

