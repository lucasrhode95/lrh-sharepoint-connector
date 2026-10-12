# SharePoint connector

A local, read-only MCP server for finding and retrieving files from OneDrive and SharePoint through
Microsoft Graph.

- Search files the signed-in account can read.
- Inspect metadata for one selected result.
- Download one selected file to this computer, within a bounded size.
- Do not crawl libraries, build a local search index, or fetch file contents as part of search.

## Ownership

The connectors follow the relationship the user is asking about:

- Outlook owns email, email attachments and calendar events.
- Teams owns chat/channel messages, message attachments and Teams meeting resources, including
  recordings, transcripts, recaps and notes.
- This connector owns general OneDrive and SharePoint file discovery and retrieval.

A file can be linked from an email or Teams message. The SharePoint connector can retrieve the stored
file, while Outlook or Teams retains responsibility for its message and relationship to that file.
A calendar event remains Outlook-owned even when it links to a Teams meeting; Teams owns the meeting
chat and artifacts.

## Requirements

- Windows, macOS or Linux.
- Python 3.12 or newer; uv.
- GitHub SSH access to the private lrh-m365-auth repository before dependency installation.
- A Microsoft 365 work or school account with access to the target files.

The connector requests the shared auth package's outlook.graph profile. It requests Graph Mail.Read
for Outlook mailbox reads and User.Read for Outlook's signed-in profile and photo; neither scope is
evidence of file access. A previous account cache had additional file/site grants, but those grants
are not a portable minimum-permission claim. A cached profile can be present while a particular
Search operation or file is denied. Microsoft Graph Search is subject to the signed-in user's
access and tenant policy.

## Install and sign in

From the repository root:

~~~powershell
uv sync --locked
uv run sharepoint-connector auth
uv run sharepoint-connector status
~~~

Any one of the three connectors can start the shared Microsoft 365 sign-in bootstrap. It checks all
five shared profiles, silently reuses accepted profiles and asks Microsoft for profiles that are
still missing. Different Microsoft clients or resource audiences can require separate device codes
and MFA approvals. The auth command exits successfully only when all five profiles are ready, so it
can report an incomplete setup even when the Graph profile this connector uses is ready. Ordinary
search and file operations do not open a login flow.

The encrypted cache is shared at %USERPROFILE%\.lrh-m365-auth by default. Set M365_AUTH_HOME to
change the location for all connectors. It is bound to one active Microsoft account. Switching
accounts clears authentication for Outlook, Teams and SharePoint:

~~~powershell
uv run sharepoint-connector auth --sign-out
uv run sharepoint-connector auth
~~~

The status command reads local profile state: whether the OAuth client credential is cached and
when a matching Graph access token expires, if present. status --check also attempts silent Graph
token acquisition; it does not prove Search, metadata or download permission. Operation-specific
Graph permission errors are reported separately from token acquisition.

## Configure a local MCP client

The server uses stdio. Replace C:\Users\you\dev\lrh-sharepoint-connector with the absolute path to
your clone.

Codex CLI:

~~~powershell
codex mcp add lrh-sharepoint-connector -- uv run --directory C:\Users\you\dev\lrh-sharepoint-connector sharepoint-connector mcp
~~~

Claude Code:

~~~powershell
claude mcp add --transport stdio lrh-sharepoint-connector -- uv run --directory C:\Users\you\dev\lrh-sharepoint-connector sharepoint-connector mcp
~~~

VS Code local MCP support, in .vscode/mcp.json:

~~~json
{
  "servers": {
    "lrh-sharepoint-connector": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\you\\dev\\lrh-sharepoint-connector",
        "sharepoint-connector",
        "mcp"
      ]
    }
  }
}
~~~

Replace the example path. PowerShell uses single backslashes; JSON and TOML strings double them. These
commands need a local client that can start an MCP process. The connector does not provide a browser
UI or a remote MCP endpoint.

## MCP tools

- search_files(query, offset=0, page_size=25, scope_url=null) asks Microsoft Search for driveItem
  results. Page size is capped at 200. The response includes Graph resource IDs, name, available
  location/type/size/date metadata, webUrl, rank, summary, total when returned, more-results state
  and next_offset. Search snippets and names are untrusted text. Search does not download content.
- get_file_metadata(drive_id, item_id) reads metadata for one selected item using the exact resource
  identifiers from a search result.
- download_file(drive_id, item_id, max_bytes=52428800) downloads one selected non-folder file.
  The default is 50 MiB; the hard maximum is 100 MiB. The response gives a local path for the agent
  to read with local file tools.

Microsoft Search hitId is not a driveItem ID. Use drive_id and item_id taken from the result's
resource object; results missing either ID can be opened by webUrl but cannot be hydrated by these
tools.

Example workflow:

1. Search for a narrow topic, such as annual budget draft.
2. Read the result snippet, location and dates. Request another page only when it could help.
3. Hydrate metadata for a promising result using its drive_id and item_id.
4. Download only the selected file if its contents are needed.

Search ranks matches; it is not exhaustive recall. An empty result can reflect indexing delay,
content-type limits, access rights, query syntax or scope constraints. Do not infer that a library
contains no matching file from one empty result. Microsoft Search does not promise a complete
organization-wide corpus outside files the signed-in account can access.

### Scope, paging and indexing

The optional scope_url adds a Graph KQL path constraint to the search query. Scoped queries accept
plain terms only, so a query cannot add KQL operators that broaden the scope. A rejected scoped
request is returned as an error; the connector never retries it without the path constraint. Use a
site, library or folder URL without query/fragment parameters. Scope behavior remains subject to
known-hit tests passed for representative OneDrive and shared SharePoint parent URLs in one
account. Other URL forms and tenants remain deployment-specific; a zero result is not proof the scope
contains no files.

Use next_offset only when more_results_available is true. The offset is explicit and stable for one
request, but Graph Search ranking and indexing can change between pages. Search returns files the
current account can access. It can match names and supported file content; it does not identify
which internal part matched, and snippets can be incomplete.

New or changed files may take time to appear in Microsoft Search. Graph does not provide an
indexing-completion signal or an exhaustive recall guarantee.

### Metadata and downloads

Metadata comes from GET /drives/{drive-id}/items/{item-id}; the exact route reference is returned
from resource.id and resource.parentReference.driveId. Metadata includes the Graph webUrl, name,
file type, size, dates and parent path when Graph returns them.

Downloads use GET /drives/{drive-id}/items/{item-id}/content. The connector streams bytes to the
local downloads directory, checks the configured maximum while receiving, rejects unsafe redirect
hosts, and does not forward the Graph bearer token to a preauthenticated download host. It keeps
the file bytes unchanged and does not extract document text. A failed or oversized transfer removes
the partial file. Existing files are not overwritten; a numeric suffix is added to a duplicate name.

Default Windows output:

~~~text
%LOCALAPPDATA%\lrh-sharepoint-connector\downloads\<account-fingerprint>\
~~~

Override the data root with SHAREPOINT_CONNECTOR_HOME. Downloads remain on disk for the user to
manage; uninstalling the connector does not delete them. They are separated by the account
fingerprint so a later shared-account switch does not return earlier downloads as current-account
data.

## Troubleshooting and data

- Missing profile: run sharepoint-connector auth in a terminal and complete Microsoft's prompts.
- Graph 403: the token may be present while file search or the selected item is not granted. Check
  the exact operation and account access; signing in again does not itself add permission.
- Graph 401: refresh or prepare the shared profile with the auth command.
- Empty results: allow time for Microsoft Search indexing; compare a known filename/content marker
  in Microsoft 365 before claiming a coverage gap.
- Throttling: wait as Graph directs, then retry. The connector applies bounded retries for transient
  reads and has no Microsoft 365 write operations.
- The connector stores no file index or search cache. Only explicitly downloaded files are kept.
- Removing this repository does not remove the shared token cache or local downloads. Signing out
  through any connector clears authentication for all three products.

## Development

~~~powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
~~~

See [requirements](docs/requirements.md), [architecture](docs/architecture.md),
[Graph API research](docs/api-research.md) and the [roadmap](docs/roadmap.md).
