# WireGuard node requirements

The backend assumes each VPN node has:

- Ubuntu 22.04
- WireGuard installed and configured
- `wg-add-client`, `wg-disable-client`, and `wg-remove-client` installed under `/usr/local/bin`
- a dedicated SSH user with narrowly scoped sudo rights
- `qrencode` installed on the node

## Required backend contract

Each script must support JSON mode:

- `wg-add-client <client_name> <ip_last_octet> --json`
- `wg-disable-client <client_name> --json`
- `wg-remove-client <client_name> --json`

The backend treats the JSON response as the source of truth for provisioning results.

## Firewall baseline

On the VPN node, allow only:

- OpenSSH
- WireGuard UDP port

Everything else should remain denied by default.
