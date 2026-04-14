class VpnClientError(Exception):
    """Base VPN integration error."""


class VpnCommandError(VpnClientError):
    """Raised when the remote WireGuard script reports a failure."""
