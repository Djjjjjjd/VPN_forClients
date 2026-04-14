from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class VpnNode:
    name: str
    host: str
    public_ip: str
    ssh_username: str
    ssh_port: int
    ssh_private_key_path: str
    remote_scripts_dir: str


@dataclass(slots=True)
class RemoteProvisionResult:
    ok: bool
    action: str
    client_name: str
    client_ip: str
    public_key: str
    config_path: str
    qr_path: str | None
    raw_payload: dict[str, Any]
