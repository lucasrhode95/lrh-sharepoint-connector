"""Domain errors translated by the MCP and CLI surfaces."""

from m365_auth import AuthError as ConnectorError


class InvalidRequest(ConnectorError):
    """An input does not satisfy a public service contract."""


class NotFound(ConnectorError):
    """A selected drive item no longer exists or is not readable."""


class Throttled(ConnectorError):
    """Microsoft Graph is throttling the request."""


class Upstream(ConnectorError):
    """Microsoft Graph could not be reached or returned an unexpected response."""


class DownloadLimitExceeded(InvalidRequest):
    """A download exceeded the connector's local size limit."""

    def __init__(self, limit_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        mebibytes, remainder = divmod(limit_bytes, 1024 * 1024)
        self.limit = f"{mebibytes} MiB" if remainder == 0 else f"{limit_bytes:,} bytes"
        super().__init__(f"The file exceeds the connector's {self.limit} download limit.")


class PermissionDenied(Upstream):
    """Microsoft denied this operation for the current account or item (HTTP 403); the sign-in itself is
    fine. A kind of ``Upstream``, so code that tolerates an upstream failure tolerates this too."""
