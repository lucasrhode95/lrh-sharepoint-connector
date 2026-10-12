# Architecture

## Layers

This is a single-user local application with one user-facing surface:

~~~text
MCP stdio -> service.Files -> remote.FileRepository -> remote.Graph -> Microsoft Graph
                                  |
                                  +-> explicitly selected local downloads
                         shared m365-auth
~~~

The MCP surface owns tool names, schemas and MCP transport. It calls the service; it does not know
Graph URLs or map wire responses. Service methods validate public inputs and own decisions about
page bounds, path scope, file size and local output. The remote adapter implements the repository
port and alone knows Graph URLs, request bodies, continuation semantics and response mapping. The
composition root lazily builds one adapter and account-bound service set on first use.

Keeping a surface layer remains useful with one MCP surface: it isolates protocol contracts from
service decisions and remote APIs. There is no browser UI, SQLite store, search index or background
task. The only durable output is a file explicitly selected by the user for download, isolated into
a folder keyed by the active account fingerprint.

## Authentication and account binding

The connector uses lrh-m365-auth and the outlook.graph profile. It creates no duplicate MSAL client
or token cache. Every public service context lookup obtains a current token, checks stable
tenant/object identity, and rebuilds the account-bound service set after an account switch. Graph
requests acquire the current profile token. Download directories are account-fingerprinted. The
shared auth cache is encrypted by the library and used by Outlook, Teams and SharePoint.

A cached credential indicates only that OAuth state exists. Graph can still deny Search, metadata or
one selected file. Search and file permission errors remain separate from sign-in readiness.

## Graph adapter

Search POSTs one driveItem entity request to /v1.0/search/query. The mapper takes actual drive/item
references from each hit's resource and parentReference. It never maps the Search hitId into an item
ID. The service exposes Graph's explicit from/size paging and moreResultsAvailable flag, while
labeling total hits informational and recall non-exhaustive.

Metadata GETs /drives/{drive-id}/items/{item-id} with a bounded property selection. Download GETs the
same item's /content route. Graph's 302 target is checked against a narrow HTTPS host suffix
allowlist; subsequent preauthenticated requests omit Authorization. The response is streamed into
an exclusively created local file, with byte counting and partial-file deletion on failure.

The adapter retries read requests a bounded number of times for throttling and transient gateway
errors, respecting numeric or date-form Retry-After values up to 30 seconds. Search POST is a
read-only operation and is safe to retry. No Graph write adapter exists.

## CLI and shared service boundary

The CLI exposes auth, status and mcp commands. Authentication is explicit; starting the MCP process
does not launch a login flow. MCP tools call the same Files service methods as each other, keeping
input bounds and file behavior consistent. Offline status distinguishes a cached OAuth client
credential from a resource-specific Graph access-token expiry; `status --check` tests token
acquisition, not file-operation permission. Local downloads are the only product data retained by
this connector.
