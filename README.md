![Local MCP clients and the read-only SharePoint connector, which searches and downloads OneDrive and SharePoint files through Microsoft Graph.](https://raw.githubusercontent.com/lucasrhode95/lrh-sharepoint-connector/main/docs/connector-overview.svg)

A local, read-only MCP server for finding and retrieving files from OneDrive and SharePoint through
Microsoft Graph.

- Search files the signed-in account can read.
- Inspect metadata for one selected result.
- Download one selected file to this computer, within a bounded size.
- Do not crawl libraries, build a local search index, or fetch file contents as part of search.

## Requirements

- Use a Microsoft 365 work or school account with access to the target files.

## Setup

1. **Install and connect.** Use the folder already open, or choose a folder if you have none.
   Reuse an existing clone when appropriate; keep it in place because the client launches it there.

   - **With a prompt:** give your local agent:
     `Install and configure https://github.com/lucasrhode95/lrh-sharepoint-connector following its README Setup section.`
     The agent handles preparation and configuration below, then guides you through sign-in.
   - **Manually:** install [Git](https://git-scm.com/downloads) and
     [uv](https://docs.astral.sh/uv/getting-started/installation/). uv supplies Python 3.12+ if needed.
     Find uv's full path with `(Get-Command uv -CommandType Application).Source` on Windows or
     `command -v uv` on macOS/Linux. If PATH cannot find it, check the installer's destination.
     Test that executable with `--version`, then clone and install:

     ```bash
     git clone https://github.com/lucasrhode95/lrh-sharepoint-connector.git
     cd lrh-sharepoint-connector
     uv sync --locked
     ```

     The shared auth library installs automatically. Use uv's full path if the shell cannot find it.
   - **Codex CLI:** after manual preparation, register with
     [Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli):

     ```bash
     codex mcp add lrh-sharepoint-connector -- "/absolute/path/to/uv" run --directory "/absolute/path/to/lrh-sharepoint-connector" sharepoint-connector mcp
     ```
   - **Claude Code CLI:** after manual preparation, register with
     [Claude Code](https://code.claude.com/docs/en/mcp):

     ```bash
     claude mcp add --transport stdio lrh-sharepoint-connector -- "/absolute/path/to/uv" run --directory "/absolute/path/to/lrh-sharepoint-connector" sharepoint-connector mcp
     ```
   - **GitHub Copilot CLI:** after manual preparation, register with
     [Copilot](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers):

     ```bash
     copilot mcp add lrh-sharepoint-connector -- "/absolute/path/to/uv" run --directory "/absolute/path/to/lrh-sharepoint-connector" sharepoint-connector mcp
     ```
   - **GitHub Copilot in VS Code:** after manual preparation, merge this server into
     `.vscode/mcp.json`, preserving existing servers
     ([VS Code guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)):

     ```json
     {
       "servers": {
         "lrh-sharepoint-connector": {
           "type": "stdio",
           "command": "/absolute/path/to/uv",
           "args": ["run", "--directory", "/absolute/path/to/lrh-sharepoint-connector", "sharepoint-connector", "mcp"]
         }
       }
     }
     ```

   Replace all sample paths with your actual executable and clone paths, including `uv.exe` on
   Windows. Use uv's full path in MCP configuration: desktop apps may have a different PATH from
   the terminal. In JSON, escape backslashes or use forward slashes.

2. **Sign in once for all Microsoft connectors.** From any installed connector's folder, run
   its `auth` command, for example here:

   ```bash
   uv run sharepoint-connector auth
   ```

   Keep this one process running. Open Microsoft's printed URL and enter each device code as it
   appears, one at a time, using your own account. An agent should relay each prompt immediately.
   Several codes can be normal: different Microsoft profiles may need separate approvals.
   Do not start another `auth` command for each repository or run sign-ins in parallel.

   Credentials go only to Microsoft; tokens stay in the shared encrypted cache
   (`%USERPROFILE%/.lrh-m365-auth` on Windows, the XDG data folder elsewhere, or `M365_AUTH_HOME`).
   Encryption is required. To switch accounts explicitly, run `auth --sign-out`, then `auth` again.

3. **Restart the client completely.** Save your work and close **all** VS Code or chat-app windows.
   On Windows, check the system tray beside the clock, including hidden icons, and Quit/Exit any
   remaining client instance. Then reopen the app. A new chat or terminal is not a full restart.
   An agent should leave these steps for you before its session ends, rather than close the app.

4. **Verify and try it.** Check cached sign-in status from the connector folder:

   ```bash
   uv run sharepoint-connector status
   ```

   This is an offline check; also confirm the tools appear in the restarted client and make a
   small read-only request, such as "Find the quarterly plan in OneDrive or SharePoint".
   An agent should report CLI and MCP verification separately, leaving any post-restart check as
   pending until it is performed.

   SharePoint has no local UI.

Use uv's full path if the terminal cannot find it. In PowerShell, prefix a quoted executable path
with `&`, for example `& "C:/path/to/uv.exe" --version`.

### Local data

Downloaded files are stored under `%USERPROFILE%/.lrh-sharepoint-connector/downloads/<account-fingerprint>/`
on Windows, and removed after seven days the next time a file is downloaded. Set
`SHAREPOINT_CONNECTOR_HOME` to override the data root.

> **Client compatibility:** These examples require a locally running agentic client that can launch a stdio MCP server. Hosted chat apps cannot start this local process, and this project provides no remote MCP endpoint. ChatGPT can still reach it through OpenAI's [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels), where your plan and workspace allow custom MCP apps; files the server saves stay on the computer running the tunnel.

## MCP tools

The MCP server exposes the tools below. Sign-in itself (`auth`) is a CLI command; `auth_status` reports offline whether it is needed. Each one's inputs, results and caveats are in [architecture](docs/architecture.md#6-mcp-tools).

| MCP tool | Service module | Behavior |
|---|---|---|
| `auth_status` | shared auth provider | Offline: the signed-in account, each profile's cached credential and token expiry, and the sign-in command |
| `search_files` | [`service/files.py`](src/sharepoint_connector/service/files.py) | Search accessible OneDrive and SharePoint files through Microsoft Search, one page at a time; pass `next_cursor` alone for the next page |
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

Logs: each `mcp` process writes a daily-rotated file under `<data directory>/logs/`, kept for seven days. Each tool call logs its name, duration and outcome; `SHAREPOINT_CONNECTOR_LOG_LEVEL` sets the level ([architecture](docs/architecture.md#5-logging)).

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
