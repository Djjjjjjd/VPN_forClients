#!/usr/bin/env bash
set -euo pipefail

WG_IF="wg0"
WG_DIR="/etc/wireguard"
STATE_DIR="/var/lib/vpn-for-clients/clients"
SERVER_PUBLIC_KEY="$(cat "${WG_DIR}/server_public.key")"
SERVER_PUBLIC_IP="${SERVER_PUBLIC_IP:-YOUR_SERVER_PUBLIC_IP}"
WG_SUBNET_BASE="${WG_SUBNET_BASE:-10.66.66}"
DNS_SERVERS="${DNS_SERVERS:-1.1.1.1, 1.0.0.1}"
JSON_MODE="false"

json_ok() {
  printf '{"ok":true,"action":"add","client_name":"%s","client_ip":"%s","public_key":"%s","config_path":"%s","qr_path":"%s"}\n' \
    "$1" "$2" "$3" "$4" "$5"
}

json_error() {
  printf '{"ok":false,"action":"add","client_name":"%s","error_code":"%s","message":"%s"}\n' \
    "${1:-}" "$2" "$3"
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
  json_error "" "invalid_arguments" "Usage: wg-add-client <client-name> <ip-last-octet> [--json]"
  exit 1
fi

CLIENT="$1"
OCTET="$2"
if [[ "${3:-}" == "--json" ]]; then
  JSON_MODE="true"
fi

if ! [[ "${CLIENT}" =~ ^[a-zA-Z0-9._-]+$ ]]; then
  json_error "${CLIENT}" "invalid_client_name" "Client name contains unsupported characters."
  exit 1
fi

if ! [[ "${OCTET}" =~ ^[0-9]+$ ]]; then
  json_error "${CLIENT}" "invalid_octet" "IP last octet must be a number."
  exit 1
fi

if [[ "${OCTET}" -lt 2 || "${OCTET}" -gt 254 ]]; then
  json_error "${CLIENT}" "invalid_octet" "IP last octet must be between 2 and 254."
  exit 1
fi

CLIENT_IP="${WG_SUBNET_BASE}.${OCTET}"
CLIENT_DIR="${STATE_DIR}/${CLIENT}"
CLIENT_PRIVATE_KEY_FILE="${CLIENT_DIR}/${CLIENT}_private.key"
CLIENT_PUBLIC_KEY_FILE="${CLIENT_DIR}/${CLIENT}_public.key"
CLIENT_CONFIG_FILE="${CLIENT_DIR}/${CLIENT}.conf"
CLIENT_QR_FILE="${CLIENT_DIR}/${CLIENT}.png"
CLIENT_META_FILE="${CLIENT_DIR}/meta.env"

mkdir -p "${CLIENT_DIR}"
chmod 700 "${CLIENT_DIR}"

if [[ -f "${CLIENT_META_FILE}" && -f "${CLIENT_CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${CLIENT_META_FILE}"
  json_ok "${CLIENT}" "${CLIENT_IP}" "${PUBLIC_KEY}" "${CONFIG_PATH}" "${QR_PATH:-}"
  exit 0
fi

wg genkey | tee "${CLIENT_PRIVATE_KEY_FILE}" | wg pubkey | tee "${CLIENT_PUBLIC_KEY_FILE}" >/dev/null
chmod 600 "${CLIENT_PRIVATE_KEY_FILE}" "${CLIENT_PUBLIC_KEY_FILE}"

CLIENT_PRIVATE_KEY="$(cat "${CLIENT_PRIVATE_KEY_FILE}")"
CLIENT_PUBLIC_KEY="$(cat "${CLIENT_PUBLIC_KEY_FILE}")"

sudo wg set "${WG_IF}" peer "${CLIENT_PUBLIC_KEY}" allowed-ips "${CLIENT_IP}/32"
sudo wg-quick save "${WG_IF}" >/dev/null

cat > "${CLIENT_CONFIG_FILE}" <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = ${CLIENT_IP}/24
DNS = ${DNS_SERVERS}

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${SERVER_PUBLIC_IP}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF

chmod 600 "${CLIENT_CONFIG_FILE}"
qrencode -o "${CLIENT_QR_FILE}" < "${CLIENT_CONFIG_FILE}"

cat > "${CLIENT_META_FILE}" <<EOF
CLIENT_NAME="${CLIENT}"
CLIENT_IP="${CLIENT_IP}"
PUBLIC_KEY="${CLIENT_PUBLIC_KEY}"
CONFIG_PATH="${CLIENT_CONFIG_FILE}"
QR_PATH="${CLIENT_QR_FILE}"
DISABLED="0"
EOF

chmod 600 "${CLIENT_META_FILE}"

json_ok "${CLIENT}" "${CLIENT_IP}" "${CLIENT_PUBLIC_KEY}" "${CLIENT_CONFIG_FILE}" "${CLIENT_QR_FILE}"
