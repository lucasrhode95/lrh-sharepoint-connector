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
    """Per-user application data directory. ``SHAREPOINT_CONNECTOR_HOME`` overrides it (tests, portability).

    On Windows it is the .lrh-sharepoint-connector folder in the user profile, outside AppData: Windows
    redirects files that packaged apps (such as the Claude desktop app, and the MCP servers it starts)
    create under AppData into a private per-app copy, which a terminal and Explorer never see.
    """
    override = os.environ.get("SHAREPOINT_CONNECTOR_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if _windows():
        return Path.home() / f".{APP_NAME}"
    root = os.environ.get("XDG_DATA_HOME")
    return (Path(root) if root else Path.home() / ".local" / "share") / APP_NAME


def _windows() -> bool:
    return os.name == "nt"
