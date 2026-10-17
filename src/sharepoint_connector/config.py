"""Named deployment settings for the local SharePoint connector."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "lrh-sharepoint-connector"

CLI_NAME = "sharepoint-connector"
GRAPH_PROFILE = "outlook.graph"
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200
MAX_OFFSET = 100_000
DEFAULT_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


def data_dir() -> Path:
    """Per-user data directory: ``SHAREPOINT_CONNECTOR_HOME``, else ``%LOCALAPPDATA%`` on Windows, else
    ``$XDG_DATA_HOME`` or ``~/.local/share``, each with ``lrh-sharepoint-connector``."""
    override = os.environ.get("SHAREPOINT_CONNECTOR_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
