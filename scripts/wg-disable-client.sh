#!/usr/bin/env bash
set -euo pipefail

WG_IF="wg0"
STATE_DIR="/var/lib/vpn-for-clients/clients"

json_ok() {
  printf '{"ok":true,"action":"disable","client_name":"%s","message":"%s"}\n' "$1" "$2"
}

json_error() {
  printf '{"ok":false,"action":"disable","client_name":"%s","error_code":"%s","message":"%s"}\n' \
    "${1:-}" "$2" "$3"
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  json_error "" "invalid_arguments" "Usage: wg-disable-client <client-name> [--json]"
  exit 1
fi

CLIENT="$1"
CLIENT_DIR="${STATE_DIR}/${CLIENT}"
CLIENT_META_FILE="${CLIENT_DIR}/meta.env"

if [[ ! -f "${CLIENT_META_FILE}" ]]; then
  json_error "${CLIENT}" "client_not_found" "Client metadata not found."
  exit 1
fi

# shellcheck disable=SC1090
source "${CLIENT_META_FILE}"

if [[ "${DISABLED:-0}" == "1" ]]; then
  json_ok "${CLIENT}" "client already disabled"
  exit 0
fi

sudo wg set "${WG_IF}" peer "${PUBLIC_KEY}" remove
sudo wg-quick save "${WG_IF}" >/dev/null

cat > "${CLIENT_META_FILE}" <<EOF
CLIENT_NAME="${CLIENT_NAME}"
CLIENT_IP="${CLIENT_IP}"
PUBLIC_KEY="${PUBLIC_KEY}"
CONFIG_PATH="${CONFIG_PATH}"
QR_PATH="${QR_PATH:-}"
DISABLED="1"
EOF

chmod 600 "${CLIENT_META_FILE}"
json_ok "${CLIENT}" "client disabled"
