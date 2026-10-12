# Microsoft Graph file API research

Date: 2026-10-11.

## Scope and evidence

This is a dated record for Graph-backed file discovery and selected reads. Public API contract
statements link to Microsoft documentation. Live results are account-, tenant-, permission- and
index-specific. Browser captures and private source bundles are not fixtures or repository inputs.

## Endpoint map

| Purpose | Request | Contract |
|---|---|---|
| Search OneDrive and SharePoint | POST https://graph.microsoft.com/v1.0/search/query | Microsoft Search request with entityTypes [driveItem], query.queryString, from and size. Search is over accessible files and folders; returned snippets/rank are relevance signals, not exhaustive coverage. |
| Hydrate selected item | GET /v1.0/drives/{drive-id}/items/{item-id}?$select=... | Use resource.id and resource.parentReference.driveId from the Search hit. Do not substitute the separate hitId. |
| Download selected item | GET /v1.0/drives/{drive-id}/items/{item-id}/content | Graph may return a redirect to a short-lived preauthenticated file URL. Do not forward the Graph Authorization header to that host. |

The same Microsoft Search endpoint supports distinct entity types for mail, Teams chat messages and
files. This connector uses driveItem only. Outlook's existing GET /me/messages?$search=... and
OWA/Substrate routes are separate mail-search mechanisms. Teams attachments remain contextual
Teams data; this driveItem search finds the stored file where accessible, not the originating message.

## Search response identity and paging

A Search hit can contain hitId, rank, summary and a resource object. DriveItem hydration is based
on resource.id plus resource.parentReference.driveId. resource.webUrl is suitable for opening a
browser link when present. Missing resource IDs mean the result can be shown but not hydrated by the
connector. The Search API uses from and size; the connector caps each page at 200 and relies on
moreResultsAvailable to offer the next offset. A returned total is informational. Relevance ranking,
indexing delay, file support and user access make this an incomplete search surface.

Microsoft documents driveItem search over OneDrive and SharePoint content available to the caller.
The same request entity serves both locations; there is not a different Search endpoint for a
personal OneDrive drive and a company SharePoint library. Metadata/download routes require the
drive/item reference returned for the chosen item.

## Scope filter

The connector encodes an optional location as a KQL path constraint. The query is not retried
unscoped after a rejection. Scoped queries accept plain search terms only, preventing query
operators from weakening the location constraint. A known-hit test on 2026-10-11 returned the expected synthetic item when scoped to a
representative OneDrive parent URL and a representative shared SharePoint parent URL. This verifies
those two path-query examples for the tested account; it does not prove every site/library URL form
or every tenant's KQL behavior. A zero result from an arbitrary path is not sufficient evidence of
unsupported syntax or empty content.

## Permissions and shared auth

The connector obtains the outlook.graph token from lrh-m365-auth. That profile requests delegated
Graph Mail.Read and User.Read for Outlook's mailbox and signed-in profile/photo features; neither is
evidence of file access. Microsoft Graph Search file permission guidance includes delegated
Files.Read.All and Sites.Read.All cases; current tenant grants may differ, and the prior live token
had broader file/site grants than the shared profile's requested scopes. Do not treat that one
account's grant set as the minimum required permission or generalize its consent outcome to other
tenants. A new sign-in may not add a missing scope unless the client/resource request and tenant
consent allow it.

**Shared-auth catalog note (2026-10-12):** the auth package now bootstraps six resource profiles,
including `m365.search` for Outlook calendar and Teams message discovery. SharePoint continues to
request `outlook.graph`; `m365.search` is not used by this connector and is not evidence of file
access. This is an implementation/catalog update, not new live permission evidence.

## Download boundary

Selected content is retrieved only after explicit download_file invocation. Downloads have a 50 MiB
default and 100 MiB hard limit. The adapter checks Content-Length when available and counts streamed
bytes. Graph's bearer is limited to graph.microsoft.com; redirect URLs must be HTTPS on SharePoint or
OneDrive file host suffixes. Redirect requests carry no Graph bearer. Signed URLs and response bodies
are never logged or persisted as metadata. Incomplete local files are removed.

## Live verification log

### 2026-10-11 — synthetic OneDrive and shared-library validation

An initial read after local upload found the OneDrive synthetic file but not the shared-library
synthetic file. After additional indexing time, later read-only Graph Search calls found the
expected file for both the filename term and the unique content-only term in both locations.
Each of the four targeted queries returned one hit, and each resource name matched the expected
synthetic file. A random negative marker returned zero. The SharePoint result's eventual visibility
confirms indexing lag in this example; the elapsed wait is not a Microsoft indexing-time guarantee.

For each location, the Search resource's drive/item references successfully hydrated metadata.
A selected download returned 13 bytes and matched the expected synthetic bytes. No identifiers,
file names, marker terms, content or signed URL were printed or retained.

A representative parent path scope returned the known hit for both OneDrive and the shared
SharePoint file. This is a deployment-specific known-hit result, not proof that every URL form or
all tenants accept the same scope syntax.

A bounded query returned five results at offset 0 and five distinct resource references at offset 5;
both pages reported more results available. Sample operation timings (one request each) were:
filename Search 1.72 s / 0.51 s, content Search 0.73 s / 0.61 s, metadata 0.88 s / 0.89 s,
selected download 1.70 s / 1.76 s, and scoped Search 0.60 s / 0.81 s, respectively for OneDrive /
SharePoint. One second-page request took 24.9 s; an immediate direct repeat returned HTTP 200 in
2.5 s without a Retry-After header. This isolated timing outlier does not establish throttling or
a stable latency distribution.

These checks establish the tested account's current access to these known items through the shared
Graph profile. They do not establish minimum permissions, exhaustive recall, general tenant
coverage, or an indexing SLA. The user's existing Graph grants include file/site permissions beyond
the shared profile's requested Mail.Read and User.Read; neither scope is evidence of file access.

## Official references

- [Microsoft Search files across OneDrive and SharePoint](https://learn.microsoft.com/en-us/graph/search-concept-files)
- [Microsoft Graph Search API overview and paging](https://learn.microsoft.com/en-us/graph/api/resources/search-api-overview?view=graph-rest-1.0)
- [SearchRequest resource](https://learn.microsoft.com/en-us/graph/api/resources/searchrequest?view=graph-rest-1.0)
- [Get a driveItem](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0)
- [Download driveItem content](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
