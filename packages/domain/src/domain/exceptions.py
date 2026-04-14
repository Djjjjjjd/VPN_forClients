class DomainError(Exception):
    """Base domain error."""


class ProvisioningError(DomainError):
    """Raised when VPN provisioning cannot be completed."""
