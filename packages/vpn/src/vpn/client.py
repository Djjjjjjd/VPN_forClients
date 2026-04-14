from __future__ import annotations

import json
from pathlib import Path

import asyncssh

from vpn.exceptions import VpnClientError, VpnCommandError
from vpn.models import RemoteProvisionResult, VpnNode


class SshWireGuardProvisioner:
    async def add_client(self, node: VpnNode, client_name: str, ip_last_octet: int) -> RemoteProvisionResult:
        command = f"{node.remote_scripts_dir}/wg-add-client {client_name} {ip_last_octet} --json"
        payload = await self._run_json_command(node, command)
        return RemoteProvisionResult(
            ok=payload["ok"],
            action=payload["action"],
            client_name=payload["client_name"],
            client_ip=payload["client_ip"],
            public_key=payload["public_key"],
            config_path=payload["config_path"],
            qr_path=payload.get("qr_path"),
            raw_payload=payload,
        )

    async def disable_client(self, node: VpnNode, client_name: str) -> dict:
        command = f"{node.remote_scripts_dir}/wg-disable-client {client_name} --json"
        return await self._run_json_command(node, command)

    async def remove_client(self, node: VpnNode, client_name: str) -> dict:
        command = f"{node.remote_scripts_dir}/wg-remove-client {client_name} --json"
        return await self._run_json_command(node, command)

    async def download_artifacts(
        self,
        node: VpnNode,
        remote_result: RemoteProvisionResult,
        local_dir: Path,
    ) -> dict[str, Path]:
        local_dir.mkdir(parents=True, exist_ok=True)
        async with asyncssh.connect(
            host=node.host,
            username=node.ssh_username,
            port=node.ssh_port,
            client_keys=[node.ssh_private_key_path],
            known_hosts=None,
        ) as connection:
            async with connection.start_sftp_client() as sftp:
                config_target = local_dir / Path(remote_result.config_path).name
                await sftp.get(remote_result.config_path, str(config_target))
                result = {"config_path": config_target}
                if remote_result.qr_path:
                    qr_target = local_dir / Path(remote_result.qr_path).name
                    await sftp.get(remote_result.qr_path, str(qr_target))
                    result["qr_path"] = qr_target
                return result

    async def _run_json_command(self, node: VpnNode, command: str) -> dict:
        async with asyncssh.connect(
            host=node.host,
            username=node.ssh_username,
            port=node.ssh_port,
            client_keys=[node.ssh_private_key_path],
            known_hosts=None,
        ) as connection:
            result = await connection.run(command, check=False)

        if result.returncode != 0:
            raise VpnCommandError(result.stderr.strip() or result.stdout.strip() or "VPN command failed")

        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as exc:
            raise VpnClientError("remote script returned invalid JSON") from exc

        if not payload.get("ok", False):
            raise VpnCommandError(payload.get("message", "VPN command failed"))

        return payload
