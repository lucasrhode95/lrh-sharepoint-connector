![Local MCP clients and the read-only SharePoint connector, which searches and downloads OneDrive and SharePoint files through Microsoft Graph.](https://raw.githubusercontent.com/lucasrhode95/lrh-sharepoint-connector/main/docs/connector-overview.svg)

A local, read-only MCP server for finding and retrieving files from OneDrive and SharePoint through
Microsoft Graph.

- Search files the signed-in account can read.
- Inspect metadata for one selected result.
- Download one selected file to this computer, within a bounded size.
- Do not crawl libraries, build a local search index, or fetch file contents as part of search.

## Requirements

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Use a Microsoft 365 work or school account with access to the target files.

A separate Python installation is optional: uv selects an installed Python 3.12 or newer, or installs a managed version when needed.

## Setup

```bash
uv sync --locked
uv run sharepoint-connector auth
uv run sharepoint-connector status
```

Run the `auth` command above and it logs you in. All `lrh-*` Microsoft 365 connectors share one login engine (`lrh-m365-auth`), so one login covers them all. Microsoft may ask for more than one approval, because the connectors use different Microsoft clients.

`status` shows the signed-in account and its cached profiles without touching the network. To switch accounts, run `auth --sign-out`, then `auth` again. Which profile serves which tool is in [architecture](docs/architecture.md#2-authentication-and-account-binding).

> Credentials are entered only on Microsoft's sign-in page. Tokens stay in the shared encrypted cache
> (`~/.lrh-m365-auth`, or `M365_AUTH_HOME`). If encryption is unavailable, sign-in fails closed.

Downloaded files are stored under `%LOCALAPPDATA%\lrh-sharepoint-connector\downloads\<account-fingerprint>\`
on Windows, and removed after seven days the next time a file is downloaded. Set
`SHAREPOINT_CONNECTOR_HOME` to override the data root.

### Configure a local MCP client

Replace `/path/to/lrh-sharepoint-connector` with the absolute path to your clone.

**Claude Code** — add the server from a terminal:

```bash
claude mcp add --transport stdio lrh-sharepoint-connector -- uv run --directory /path/to/lrh-sharepoint-connector sharepoint-connector mcp
```

See the [Claude Code MCP guide](https://docs.anthropic.com/en/docs/claude-code/mcp).

**Codex CLI** — register the same stdio command:

```bash
codex mcp add lrh-sharepoint-connector -- uv run --directory /path/to/lrh-sharepoint-connector sharepoint-connector mcp
```

See the [Codex MCP guide](https://developers.openai.com/codex/mcp/).

**GitHub Copilot Chat in VS Code** — add this server to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "lrh-sharepoint-connector": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/lrh-sharepoint-connector",
        "sharepoint-connector",
        "mcp"
      ]
    }
  }
}
```

Replace the sample path with your clone’s absolute path. In Windows JSON paths, escape backslashes (for example, `C:\\Users\\you\\lrh-sharepoint-connector`). This example requires Copilot Chat’s Agent mode with local MCP support; see [VS Code’s MCP guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers).

> **Client compatibility:** These examples require a locally running agentic client that can launch a stdio MCP server. Hosted chat apps cannot start this local process, and this project provides no remote MCP endpoint. ChatGPT can still reach it through OpenAI's [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels), where your plan and workspace allow custom MCP apps; files the server saves stay on the computer running the tunnel.

## MCP tools

The MCP server exposes the tools below; authentication and status are CLI commands, not MCP tools. Each one's inputs, results and caveats are in [architecture](docs/architecture.md#6-mcp-tools).

| MCP tool | Service module | Behavior |
|---|---|---|
| `search_files` | [`service/files.py`](src/sharepoint_connector/service/files.py) | Search accessible OneDrive and SharePoint files through Microsoft Search, one page at a time |
| `get_file_metadata` | [`service/files.py`](src/sharepoint_connector/service/files.py) | Read metadata for one selected result |
| `download_file` | [`service/files.py`](src/sharepoint_connector/service/files.py) | Download one selected file locally (50 MiB by default, 100 MiB at most) |

## Microsoft 365 connectors

This repository is part of the `lrh-*` **Microsoft 365** connectors: local tools that give MCP agents
access to a common corporate environment, its mail and calendar, chats and meetings, and files. Each
repository owns one product, and all of them share one sign-in.

<table>
  <tr><th width="270" nowrap>Repository</th><th>Responsible for</th></tr>
  <tr><td nowrap><picture><img src="https://raw.githubusercontent.com/lucasrhode95/lrh-m365-auth/main/docs/logos/entra-id.svg" height="29" align="absmiddle" alt="Entra ID"></picture>&nbsp;<a href="https://github.com/lucasrhode95/lrh-m365-auth">lrh-m365-auth</a></td><td>Shared <b>Microsoft</b> sign-in through <b>Entra ID</b>: one encrypted token cache and the profiles every connector uses</td></tr>
  <tr><td nowrap><picture><img src="https://raw.githubusercontent.com/lucasrhode95/lrh-m365-auth/main/docs/logos/outlook.svg" height="24" align="absmiddle" alt="Outlook"></picture>&nbsp;<a href="https://github.com/lucasrhode95/lrh-outlook-connector">lrh-outlook-connector</a></td><td><b>Exchange</b> mail, folders, drafts, rules, native signatures, and calendar events (schedule, agenda, attendees, <b>Teams</b> join link)</td></tr>
  <tr><td nowrap><picture><img src="https://raw.githubusercontent.com/lucasrhode95/lrh-m365-auth/main/docs/logos/teams.svg" height="24" align="absmiddle" alt="Teams"></picture>&nbsp;<a href="https://github.com/lucasrhode95/lrh-teams-connector">lrh-teams-connector</a></td><td><b>Teams</b> chats and channels, message attachments, and meeting chats, recordings, transcripts, recaps and notes</td></tr>
  <tr><td nowrap><picture><img src="https://raw.githubusercontent.com/lucasrhode95/lrh-m365-auth/main/docs/logos/sharepoint.svg" height="24" align="absmiddle" alt="SharePoint"></picture>&nbsp;<a href="https://github.com/lucasrhode95/lrh-sharepoint-connector">lrh-sharepoint-connector</a></td><td>General <b>OneDrive</b> and <b>SharePoint</b> file search and selected file retrieval (read-only)</td></tr>
</table>

A calendar event stays with **Outlook** even when it links to a **Teams** meeting; **Teams** owns that
meeting's chat and artifacts. A file linked from an email or a **Teams** message stays part of that
message, while the stored file itself is retrieved through **SharePoint**. Only verified identifiers
connect records across products.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

`lrh-m365-auth` follows its `main` branch, and `uv.lock` records the exact commit. Run
`uv lock --upgrade-package lrh-m365-auth` to move to its latest commit.

Logs: each `mcp` process writes a daily-rotated file under `<data directory>/logs/`, kept for seven days. Set `SHAREPOINT_CONNECTOR_LOG_LEVEL=DEBUG` for request timings ([architecture](docs/architecture.md#5-logging)).

Project references: [documentation index](docs/README.md) · [requirements](docs/requirements.md) · [architecture](docs/architecture.md) · [Graph API research](docs/api-research.md) · [roadmap](docs/roadmap.md).

## Disclaimer

> [!WARNING]
> Unofficial: these tools sign in as Microsoft's own apps and use undocumented services. Check your
> organization's AI and data policies before giving an agent your work data. Provided as is, without
> warranty. Microsoft, Outlook, Teams, SharePoint and Entra are Microsoft trademarks; this project is
> not affiliated with Microsoft.

## License

Copyright 2026 Lucas Rhode. This is source-available software, not open source: the code is public
so anyone can read and audit it. The [PolyForm Internal Use License 1.0.0](LICENSE.md) lets you and
your company use and adapt the software for your own internal operations, including at work. The
licensor also permits personal, noncommercial use. Serving other companies with it is not internal
use: you may not sell it, ship it in a product, or offer it as a service, and you may not distribute
the software or a modified copy of it.
