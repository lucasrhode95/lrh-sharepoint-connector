# SharePoint connector requirements

Date: 2026-10-12.

## 1. Product

A local, read-only connector for finding and retrieving general files in the signed-in user's
OneDrive and SharePoint.

## 2. Ownership (2026-10-17)

The same in every `lrh-*` connector. Each connector owns one product, and all share one sign-in
(`lrh-m365-auth`):

- **Outlook** owns Exchange mail and its attachments, and calendar events: schedule, recurrence, agenda,
  organizer, invitees, event attachment metadata and any join link.
- **Teams** owns chats and channels, message attachments, and a Teams meeting's chat, recordings,
  transcripts, recap and notes.
- **SharePoint** owns discovery and retrieval of general OneDrive and SharePoint files.

A file linked from an email or a Teams message stays part of that message; the stored file itself is
retrieved through SharePoint. Only verified identifiers connect records across products. A shared
search endpoint, or a similar name, does not change who owns a resource, and a meeting on another
platform does not become a Teams meeting.

## 3. Read-only capabilities

1. Search accessible OneDrive/SharePoint driveItems with Microsoft Graph Search. Return compact
   result identity, name, link, available metadata, rank and snippet.
2. Page results explicitly so an agent can decide whether to retrieve more.
3. Hydrate metadata for one selected item from its drive/item identifiers.
4. Download one selected non-folder item as original bytes to a local, account-scoped output folder
   with a conservative default and hard byte limit.
5. Expose the service through one stdio MCP surface.

Search never downloads file bodies. There is no local content index, background crawler, scheduler,
browser UI, remote MCP endpoint, text extraction from file formats, upload, sharing change, permission
mutation, delete, rename, move or organization-wide access claim.

## 4. Search contracts

- Search uses Microsoft Graph POST /v1.0/search/query with entityTypes driveItem.
- The resource object's parentReference.driveId and resource.id are the hydration references.
  Microsoft Search hitId is not interchangeable with a driveItem ID.
- Page size defaults to 25 and is capped at 200. Paging uses an opaque `next_cursor` that carries the query,
  scope, page size and position; the offset stays internal. Graph's moreResultsAvailable controls whether a
  next cursor is offered; a total is informational.
- Graph results are relevance ranked, constrained by the active user's access, and can lag file
  changes. The connector makes no exhaustive recall or immediate-indexing promise.
- Optional path scope is encoded into the query and must not silently fall back to an unscoped
  request. Known-hit scope tests passed for representative OneDrive and shared SharePoint parent URLs
  in the tested account; this does not establish every URL form or tenant behavior.

## 5. Access and persistence

The connector uses the shared `outlook.graph` profile through lrh-m365-auth. The shared auth
catalog bootstraps six profiles, including `m365.search` for Outlook calendar and Teams message
discovery; this connector does not use that profile, and it does not authorize file operations.
Token-cache presence does not prove a Graph operation or file is authorized. Microsoft delegated
permissions, tenant consent, account grants and each item's access are distinct. No
connector-specific plaintext token cache is created.

The connector stores no durable search index or file metadata cache. A selected download is streamed
with a default 50 MiB limit and a hard 100 MiB cap, to an exclusive account-fingerprinted output
folder. Redirects from Graph must use an approved Microsoft file host, and the bearer token is never
sent to that host. A failed transfer removes partial output.

## 6. User and operator behavior

Authentication bootstrap is explicit; ordinary data calls remain silent. Account switching uses the
shared auth package's single-account binding and isolates local download directories by account
fingerprint. The MCP surface delegates to the shared service; the service depends on a remote port,
not concrete Graph wire details.

Offline status reports cached OAuth client credentials separately from a cached Graph access-token
expiry. `status --check` attempts token acquisition but does not prove Search, metadata or download
authorization.

## 7. Acceptance evidence

Deterministic tests use synthetic Graph responses. Live verification is deployment-specific and
must separately cover a personal OneDrive item and a company SharePoint item, filename and
content-only known terms, negative controls, paging, selected metadata/content retrieval, and any
scope mode. Unverified account grants or indexing outcomes are reported as such.
