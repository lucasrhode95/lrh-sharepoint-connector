"""Domain errors translated by the MCP and CLI surfaces."""

from m365_auth import AuthError as ConnectorError


class InvalidRequest(ConnectorError):
    """An input does not satisfy a public service contract."""


class PermissionDenied(ConnectorError):
    """Microsoft Graph denied this operation for the current account or item."""


class NotFound(ConnectorError):
    """A selected drive item no longer exists or is not readable."""


class Throttled(ConnectorError):
    """Microsoft Graph is throttling the request."""


class Upstream(ConnectorError):
    """Microsoft Graph could not be reached or returned an unexpected response."""


class DownloadLimitExceeded(InvalidRequest):
    """The selected item exceeds the configured local download limit."""

    def __init__(self, limit_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        super().__init__(f"The selected file exceeds the {limit_bytes} byte download limit.")
