from ipaddress import ip_address

from domain.exceptions import ProvisioningError
from domain.schemas import ServerCandidate


def choose_server(candidates: list[ServerCandidate]) -> ServerCandidate:
    available = [
        candidate
        for candidate in candidates
        if candidate.max_clients is None or candidate.active_clients < candidate.max_clients
    ]
    if not available:
        raise ProvisioningError("no active VPN servers available")

    return min(available, key=lambda candidate: (candidate.active_clients, candidate.priority, candidate.id))


def pick_next_ip_last_octet(used_ips: list[str]) -> int:
    used_octets = {int(str(ip_address(ip)).split(".")[-1]) for ip in used_ips}
    for octet in range(2, 255):
        if octet not in used_octets:
            return octet
    raise ProvisioningError("no free IP addresses left in subnet")
