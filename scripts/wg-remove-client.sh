#!/usr/bin/env bash
set -euo pipefail

WG_IF="wg0"
STATE_DIR="/var/lib/vpn-for-clients/clients"

json_ok() {
  printf '{"ok":true,"action":"remove","client_name":"%s","message":"%s"}\n' "$1" "$2"
}

json_error() {
  printf '{"ok":false,"action":"remove","client_name":"%s","error_code":"%s","message":"%s"}\n' \
    "${1:-}" "$2" "$3"
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  json_error "" "invalid_arguments" "Usage: wg-remove-client <client-name> [--json]"
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

if sudo wg show "${WG_IF}" peers | grep -q "^${PUBLIC_KEY}$"; then
  sudo wg set "${WG_IF}" peer "${PUBLIC_KEY}" remove
  sudo wg-quick save "${WG_IF}" >/dev/null
fi

rm -rf "${CLIENT_DIR}"
json_ok "${CLIENT}" "client removed"
