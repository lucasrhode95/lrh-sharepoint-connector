# SharePoint connector roadmap

Updated: 2026-10-11.

## Implemented in initial read-only connector

- Shared authentication through the outlook.graph profile.
- Offline status distinguishes cached client credentials from resource-token expiry; token
  acquisition does not prove Graph file access.
- Microsoft Graph Search for driveItem with explicit offset paging and a conservative page cap.
- Resource-level drive/item reference mapping; no hitId-to-itemId assumption.
- Selected metadata hydration and bounded selected-file download.
- One stdio MCP surface over a separate service layer and Graph adapter.
- Synthetic tests cover mapping, validation, paging flags, redirect credential boundaries, file size
  limits, partial cleanup, account-bound output directories and MCP tool contracts.

## Live validation for the tested account

- Filename and content-only searches found both synthetic known items after the shared-library item
  finished indexing. A negative marker returned zero.
- The resource references hydrated metadata and downloaded the selected 13-byte synthetic files;
  bytes matched the expected local files.
- Known-hit path scopes returned the expected item in OneDrive and the shared SharePoint library.
- Explicit offsets returned two distinct five-result pages. One page request had a 24.9-second
  latency outlier; an immediate direct repeat took 2.5 seconds without Retry-After, so throttling
  was not established.
- Permission minimums and exhaustive recall remain unproven. The account's existing file/site grants
  are broader than the shared auth profile's requested Mail.Read and User.Read; neither requested
  scope is evidence of file access.

## Deferred product work

No whole-library crawler or local index; no email or Teams attachment ownership; no email, calendar,
Teams message or meeting-artifact search; no sharing/permission changes; no uploads or mutations;
no broad file-type extraction; no browser UI or remote MCP endpoint.
