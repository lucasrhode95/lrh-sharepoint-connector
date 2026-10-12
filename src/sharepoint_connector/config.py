"""Named deployment settings for the local SharePoint connector."""

CLI_NAME = "sharepoint-connector"
GRAPH_PROFILE = "outlook.graph"
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200
MAX_OFFSET = 100_000
DEFAULT_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
