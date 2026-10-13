# SharePoint connector

A local, read-only MCP server for finding and retrieving files from OneDrive and SharePoint through
Microsoft Graph.

- Search files the signed-in account can read.
- Inspect metadata for one selected result.
- Download one selected file to this computer, within a bounded size.
- Do not crawl libraries, build a local search index, or fetch file contents as part of search.

## Microsoft 365 connectors

This repository is part of the `lrh-*` Microsoft 365 connectors: local tools that give MCP agents
access to a common corporate environment, its mail and calendar, chats and meetings, and files. Each
repository owns one product, and all of them share one sign-in.

| | Repository | Responsible for |
|---|---|---|
| <img src="docs/logos/entra-id.svg" height="20" alt="Entra ID"> | [lrh-m365-auth](https://github.com/lucasrhode95/lrh-m365-auth) | Shared Microsoft sign-in: one encrypted token cache and the profiles every connector uses |
| <img src="docs/logos/outlook.svg" height="20" alt="Outlook"> | [lrh-outlook-connector](https://github.com/lucasrhode95/lrh-outlook-connector) | Exchange mail, folders, drafts, rules, native signatures, and calendar events (schedule, agenda, attendees, Teams join link) |
| <img src="docs/logos/teams.svg" height="20" alt="Teams"> | [lrh-teams-connector](https://github.com/lucasrhode95/lrh-teams-connector) | Teams chats and channels, message attachments, and meeting chats, recordings, transcripts, recaps and notes |
| <img src="docs/logos/sharepoint.svg" height="20" alt="SharePoint"> | [lrh-sharepoint-connector](https://github.com/lucasrhode95/lrh-sharepoint-connector) | General OneDrive and SharePoint file search and selected file retrieval (read-only) |

A calendar event stays with Outlook even when it links to a Teams meeting; Teams owns that meeting's
chat and artifacts. A file linked from an email or a Teams message stays part of that message, while
the stored file itself is retrieved through SharePoint. Only verified identifiers connect records
across products.

## Requirements

- Windows, macOS or Linux.
- Python 3.12 or newer; uv.
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
six shared profiles, silently reuses accepted profiles and asks Microsoft for profiles that are
still missing. Different Microsoft clients or resource audiences can require separate device codes
and MFA approvals. The auth command exits successfully only when all six profiles are ready, so it
can report an incomplete setup even when the Graph profile this connector uses is ready. Ordinary
search and file operations do not open a login flow.

The `m365.search` profile is also bootstrapped here because the profile catalog is shared; Outlook
uses it for calendar search and Teams uses it for online message discovery. It does not authorize
SharePoint or OneDrive file operations.

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

See the [Claude Code MCP guide](https://docs.anthropic.com/en/docs/claude-code/mcp).

Claude Desktop and Claude web:

- Claude Desktop's current local-server flow installs a `.mcpb` desktop extension. This repository
  does not currently package one. Use Claude Code for the direct local stdio setup above; see
  [Claude Desktop local MCP setup](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
  for the extension flow.
- Claude web custom connectors use remote MCP. This repository has no remote MCP endpoint, so it
  cannot be added there directly. See
  [Anthropic's remote MCP connector guide](https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers).

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
UI or a hosted remote MCP endpoint.

### ChatGPT web through Secure MCP Tunnel

ChatGPT cannot launch a local stdio server directly. OpenAI's Secure MCP Tunnel can connect a
supported ChatGPT custom MCP app to this local server without making the server publicly reachable.
This is an optional OpenAI Platform setup, separate from the local Codex/Claude Code commands above.

You need a tunnel associated with the target ChatGPT workspace and Platform organization, its
`tunnel_id`, a runtime API key for `tunnel-client`, and permission to use custom MCP apps and tunnels.
Availability depends on the ChatGPT plan and workspace settings; check the current
[ChatGPT MCP app availability](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
and [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

Install `tunnel-client` using the download provided in Platform tunnel settings. In PowerShell, set
the runtime key and create a stdio profile, replacing the tunnel ID and repository path:

~~~powershell
$env:CONTROL_PLANE_API_KEY = "<runtime-api-key>"
tunnel-client init --sample sample_mcp_stdio_local --profile sharepoint --tunnel-id "<tunnel-id>" --mcp-command 'uv run --directory "C:\Users\you\dev\lrh-sharepoint-connector" sharepoint-connector mcp'
tunnel-client doctor --profile sharepoint --explain
tunnel-client run --profile sharepoint
~~~

Keep `tunnel-client run` running while ChatGPT uses the app. In ChatGPT web, open Settings or
workspace settings, create a custom MCP app, choose the tunnel connection, select this tunnel, scan
the tools, and create the app. Developer mode, workspace authorization and Platform tunnel
permissions may require an administrator. The tunnel client uses the connector's local shared auth
cache; do not copy that cache or its secrets into the MCP app configuration.

ChatGPT can receive search results and metadata from this server. `download_file` saves the selected
file on the computer running the tunnel client and returns its local path; hosted ChatGPT cannot
read that path. Reading downloaded file contents from ChatGPT would need an additional content-returning
or file-transfer capability, which this connector does not currently provide.

For local-client troubleshooting, restart or reload that client after changing its MCP configuration
and confirm the `search_files`, `get_file_metadata` and `download_file` tools appear in its MCP tool
list. The OpenAI tunnel flow instead shows the tools after the app scans a healthy, running tunnel.

## MCP tools

The stdio server exposes exactly these three tools. Authentication and status are CLI commands,
not MCP tools.

### Search and inspect

- `search_files(query, offset=0, page_size=25, scope_url=null)` — asks Microsoft Search for driveItem
  results. Page size is capped at 200. The response includes Graph resource IDs, name, available
  location/type/size/date metadata, webUrl, rank, summary, total when returned, more-results state
  and next_offset. Search snippets and names are untrusted text. Search does not download content.
- `get_file_metadata(drive_id, item_id)` — reads metadata for one selected item using the exact resource
  identifiers from a search result.

### Retrieve a file

- `download_file(drive_id, item_id, max_bytes=52428800)` — downloads one selected non-folder file.
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

## Disclaimer

> [!WARNING]
> These tools sign in as Microsoft's own apps and use undocumented Outlook and Teams services.
> Giving an AI agent access to your work mail, chats or files may break your organization's policies
> on AI use and data handling, so check with your IT or security team first. The tools are provided
> as is, without warranty, and the authors are not responsible for any misuse or its consequences.
> Microsoft, Outlook, Teams, SharePoint and Entra are trademarks of Microsoft; this project is not
> affiliated with or endorsed by Microsoft.

## License

Copyright 2026 Lucas Rhode. This is source-available software, not open source: the code is public
so anyone can read and audit it. The [PolyForm Internal Use License 1.0.0](LICENSE.md) lets you and
your company use and adapt the software for your own internal operations, including at work. The
licensor also permits personal, noncommercial use. Serving other companies with it is not internal
use: you may not sell it, ship it in a product, or offer it as a service, and you may not distribute
the software or a modified copy of it.
