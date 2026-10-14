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

## File and cross-category search feasibility (2026-10-07)

Public contracts: [site resolution](https://learn.microsoft.com/en-us/graph/api/site-getbypath?view=graph-rest-1.0),
[file download](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0),
[sharing links](https://learn.microsoft.com/en-us/graph/api/shares-get?view=graph-rest-1.0),
[file search and filters](https://learn.microsoft.com/en-us/graph/search-concept-files),
[search request parameters](https://learn.microsoft.com/en-us/graph/api/resources/searchrequest?view=graph-rest-1.0),
[mail search limitations](https://learn.microsoft.com/en-us/graph/search-concept-messages),
[people search](https://learn.microsoft.com/en-us/graph/search-concept-person)
and [calendar search](https://learn.microsoft.com/en-us/graph/search-concept-events).
Use those for request/response schemas, pagination, query filters and redirect handling.

**Authentication evidence:** the existing encrypted Outlook `graph` sign-in resolved an
owner-supplied workbook, obtained its metadata, and read the beginning of its download with
HTTP 200 and an XLSX-compatible header. No new scopes or interactive sign-in were required.
The full file was not downloaded, so complete-content integrity is unverified.

| Probe with the same sign-in | Observed result | Remaining uncertainty |
|---|---|---|
| Known workbook filename search (`driveItem`) | HTTP 200; expected workbook found | No exhaustive recall or pagination test |
| Generic file search without a location restriction | HTTP 200; results from multiple SharePoint sites and OneDrive | No proof of complete coverage of all accessible files |
| Known colleague name (`person`) | HTTP 200; two hits | Wider person/group coverage untested |
| Mail keyword, subject and body searches | HTTP 200; hits returned | Product folder exclusions were not applied; use official count limitations |
| Calendar event search (`event`) | HTTP 403 `Forbidden`, requiring `Calendars.Read` or `Calendars.ReadWrite` | Current Graph token lacks these scopes; another approved auth route is unproven |
| Site search and a folder-only file query | HTTP 200; zero hits | No known-hit validation; zero hits establish neither complete coverage nor lack of support |

The sharing-link resolver was not tested: the workbook was addressed through its site/library
path. Do not infer that arbitrary sharing URLs, guest resources or other tenants work.
No file, sharing permission or mailbox was changed; credentials and private results were not
retained in Git.

**Related evidence:** the Teams roadmap records successful Graph OneDrive reads and
`driveItem` search on 2026-10-01 (`lrh-teams-connector/docs/roadmap.md`, G1).
This is evidence from that repo, not a repeated Teams sign-in test. Its heterogeneous private
Substrate Search v2 discovery remains pending; Graph results do not validate that contract.
Product scope and implementation decisions for general OneDrive/SharePoint files belong in the
[SharePoint connector roadmap](https://github.com/lucasrhode95/lrh-sharepoint-connector/blob/main/docs/roadmap.md).

## Microsoft 365 Search API coverage review (2026-10-10)

**Evidence:** DOCUMENTED in Microsoft Graph v1.0 documentation (moved from the Outlook connector's research, where the review covered all products).

| Area | Documented Graph capability | Connector decision or remaining gap |
|---|---|---|
| SharePoint and OneDrive | Microsoft Search accepts `driveItem`, `listItem`, `list` and `site`; an all-content query is scoped to content the signed-in user can read. File queries support KQL such as `path:` and `filetype:`. | “Whole organization” must not mean content outside the signed-in user's access. The earlier known-file result does not prove content-only matching, exhaustive recall, personal/shared scope parity, or arbitrary share-link resolution. |

## Attachment and file discovery endpoint confirmation (2026-10-11)

Microsoft Search in Graph uses `POST /v1.0/search/query`; `requests[].entityTypes` selects the content source (moved from the Outlook connector's research).

| Search target | Graph request | Documented coverage and observed limits |
|---|---|---|
| OneDrive and SharePoint files/folders | `POST /v1.0/search/query`, `entityTypes=["driveItem"]` | Same Graph Search endpoint and entity type for both storage locations; results are restricted to items the signed-in user can read. The current profile returned a known filename hit, a known content-term hit, and broad results from multiple SharePoint sites and OneDrive. Those samples do not establish exhaustive coverage or a permission minimum. |

**Other file route, narrower scope.** Microsoft also documents DriveItem search routes such as `GET /me/drive/root/search(q='...')` for a drive hierarchy and `GET /me/drive/search(q='...')` to search more broadly for items accessible to the user. These are separate GET routes from Microsoft Search `POST /search/query`; they are useful when an explicitly drive-scoped search is desired, but were not benchmarked here.

**Implementation and validation status (2026-10-12).** The separate read-only SharePoint connector now implements `driveItem` search, explicit offset paging, returned drive/item identity mapping, selected metadata hydration, and bounded user-selected downloads. Live checks covered filename-only and content-only hits in personal OneDrive and a shared SharePoint library, selected-item metadata/download, a negative marker, and two distinct result pages. This does not establish exhaustive recall or minimum permissions: the account's existing file/site grants exceed the connector's requested Graph scopes. The connector's deployment-specific results and remaining limits are in the [SharePoint roadmap](https://github.com/lucasrhode95/lrh-sharepoint-connector/blob/main/docs/roadmap.md). Microsoft documents up to 1,000 file results per page and recommends smaller pages for latency; no indexing-time guarantee was found. Keep downloads user-selected rather than fetching a corpus during search.

## Microsoft 365 search capture and source route map: SharePoint and OneDrive (2026-10-10)

**Evidence:** CAPTURED from browser HARs and SOURCE from client bundles (moved from the Outlook connector's cross-product route map). Browser success does not prove a connector can use these private routes with app-owned authentication.

| Surface | Captured/source contract | What remains unproven |
|---|---|---|
| OneDrive Files UI | Two submitted file searches used `POST /search/api/v2/query` with `EntityRequests[].EntityType=File`, query text, `From=0`, `Size=8`, content sources, sort and fields. Two additional SharePoint REST proxy searches used `POST /_api/sp.searchresultitemcollection.getsearchresultsasstream?scenario=...&textDecorations=...` with a JSON `payload`. All four returned HTTP 200 and Search-shaped envelopes with `EntitySets[].ResultSets[].Results`; paging fields included `Total` and `MoreResultsAvailable`. | This browser surface uses Substrate plus a SharePoint proxy; neither path is Graph Search API. Result-to-Graph identity mapping, complete scope, and an advancing page request remain unproven. |
| Company SharePoint search page | Four submitted requests used `POST /searchservice/api/v2/query`; captured entity requests included `File` and `People`. Three HTTP 200 responses had result sets and one returned only `ApiVersion`, `SearchTerms`, and `Instrumentation`. The page also used `GET /search/api/v1/suggestions`, `GET /search/api/v2/init`, `GET /search/api/v2/resources`, and `POST /search/api/v1/userconfig`. | A separate Substrate-backed SharePoint page flow. Suggestion/init/config calls are not submitted-result calls. Search scope and result-to-Graph identity mapping remain unproven. |
| SharePoint result preview | `GET /api/v1/documents/searchpreview` was called 24 times with query-key names `documentType`, `listId`, `siteId`, `spWebUrl`, `uniqueId`, and `webId`; all returned `image/jpeg`. | Each preview request's `uniqueId`, `siteId`, `webId`, and `listId` matched those fields in a captured Search result `Source` record in the same HAR. This proves item-level preview/result identity, but not that a user clicked each item, that the preview is file content, or that the SharePoint IDs map to Graph drive/item IDs. |

**Captured response and paging details (2026-10-10).** The OneDrive Files UI flow had four
successful submitted searches: two `POST /search/api/v2/query` calls with `From=0`, `Size=8`, then
two SharePoint proxy POSTs under `/{site}/{scope}/_api/{operation}` with `From=0`, `Size=25`.
Observed result counts were 8, 8, 13 and 25. The later requests used SharePoint; the last also
requested OneDriveBusiness. Responses used `EntitySets[].ResultSets[].Results` and exposed `Total`
and `MoreResultsAvailable`. These are captured request/response facts, not evidence that the
private route is portable or that each item can be downloaded.

**Additional endpoint reconciliation (2026-10-11, October 10 HARs).** In the OneDrive Files UI,
the two SharePoint REST `getSearchResultsAsStream` calls are distinct from the two Search API
`/search/api/v2/query` calls. Six `SP.List.GetListDataAsStream` calls and two
`RenderListDataAsStream` calls also loaded list content; these are list/browse hydration, not
additional global searches. The company SharePoint search page instead submitted through
`/searchservice/api/v2/query`, with `GET /search/api/v1/suggestions` for suggestions. Its
`/search/api/v1/events` requests are telemetry, and `/search/api/v1/userconfig` plus
`/search/api/v2/init` are setup/configuration calls. The `GET /search/api/v2/resources` responses
were resource payloads, not result pages.

The SharePoint page's 24 successful `GET /api/v1/documents/searchpreview` responses were JPEG
images. For all 24 requests, the query values for `uniqueId`, `siteId`, `webId`, and `listId` matched
the corresponding four fields on a Search result `Source` record in that same HAR. This links each
preview to a specific search-result item. It does not prove a user click caused the request (the
page may preload previews), expose a file-content/open route, or map those SharePoint IDs to Graph
drive/item IDs.
Similarly, the OneDrive REST proxy search responses had `MoreResultsAvailable` in the envelope,
but every observed submitted offset remained zero and no next-page request was captured. These
routes are separate from Graph `POST /v1.0/search/query` with `entityTypes=["driveItem"]`.

**SharePoint client-source pagination and result identity (2026-10-11).** The supplied SharePoint
client assets contain two Search v2 request builders. `fetchScopedQueryAPI` builds a File request
to Substrate `/search/api/v2/query` with `From=0`, `Size=5`, selected fields, highlighting, sort,
merge and content-source settings; its client cache is keyed by `searchText` and has a 600,000 ms
item lifetime. A separate Lists Home provider builds File requests with `Size=24` and
`From=startRow`; its UI advances `startRow` by 24 when `MoreResultsAvailable` is true, and its
response parser reads `EntitySets[0].ResultSets[0]`. The HAR showed only offset-zero submitted
requests, so offset continuation is established in source but not exercised on the wire. The
source callers have not been traced one-to-one to individual HAR entries, and the captured company
SharePoint page's submitted result calls used `/searchservice/api/v2/query`; do not conflate that
route with these source-built `/search/api/v2/query` requests. The cache duration describes this
client cache, not server indexing delay or request latency.

The Lists Home result parser preserves SharePoint fields including `AccessUrl`, `SPWebUrl`,
`SpoUniqueId`, `SiteId`, `WebId`, `ListId`, and `ParentLink`; browser navigation can use `AccessUrl`
or combine the SharePoint URL with the unique item ID. This identifies a result within SharePoint,
but does not establish a mapping to Graph `driveId`/`itemId`. The `searchpreview` source builder
uses a dynamic API host, the observed site/list/item identity keys, a `ClientScenario` header, and
returns an image blob through an object URL. That source explains preview hydration; it does not
establish that every preview request follows a user click or that it returns file content.

## SharePoint connector follow-up: live file hydration and scope (2026-10-11)

The later shared-auth validation completed the file checks that were open in the earlier note above.
For a synthetic file in personal OneDrive and another in the shared company SharePoint library,
the same POST /v1.0/search/query request with entityTypes=["driveItem"] returned one filename
hit and one content-only hit per location. The shared-library file was initially absent from Search
and appeared after additional indexing time; this example does not establish an indexing SLA.
A random negative marker returned zero.

For both results, the resource's parentReference.driveId and id hydrated the selected item through
GET /v1.0/drives/{drive-id}/items/{item-id} and downloaded its 13-byte synthetic content through
GET /v1.0/drives/{drive-id}/items/{item-id}/content. The bytes matched the local test files.
Representative path: KQL scopes returned the known hit for both the OneDrive parent and shared
SharePoint parent. This validates those examples for this account, not every path form or tenant.

A bounded five-result query returned five distinct resources at offsets 0 and 5, with
moreResultsAvailable=true. Sample operation timings were approximately 0.5–1.8 seconds for each
filename/content search, metadata lookup, selected download and known-hit scoped search. One second
page call took 24.9 seconds; an immediate direct repeat took 2.5 seconds and returned no
Retry-After header. That isolated latency outlier does not establish throttling or a stable
performance distribution.

These live requests used the shared outlook.graph profile. The profile requests Mail.Read and
User.Read; the current account's token grants include broader file/site permissions recorded in the Outlook connector's research §3.1. Successful file reads therefore prove this account's current capability, not a minimum
permission set or that either requested scope authorizes Microsoft Search files. Search remains
limited to accessible items and non-exhaustive. No file names, markers, IDs, URLs or content were
retained.

## Cross-product search ledger: SharePoint and OneDrive (2026-10-12)

Moved from the Outlook connector's former cross-product index (`m365-search-findings.md`).

**Graph link:** the file search here uses Graph Search API `driveItem`; see the Graph table below for the shared request family and its differences from mail and Teams search.

SharePoint/OneDrive file search was investigated separately from Outlook mail and Teams global search. The observed Graph route was `POST /v1.0/search/query` with `entityTypes: ["driveItem"]`; synthetic filename-only and content-only queries returned hits. The read-only SharePoint connector now uses this route, preserves returned drive/item identity, hydrates selected metadata, and supports bounded downloads. Live checks found synthetic known items in personal OneDrive and a shared SharePoint library, hydrated their metadata, downloaded matching bytes, and returned distinct pages for explicit offsets. The account's permissions exceed the connector's requested Graph scopes, so minimum permissions and exhaustive recall remain unverified; see the [SharePoint roadmap](https://github.com/lucasrhode95/lrh-sharepoint-connector/blob/main/docs/roadmap.md).

The web routes now resolve by surface. The OneDrive Files flow submitted Substrate `POST /search/api/v2/query` for `File` and also used the SharePoint REST proxy `POST /_api/sp.searchresultitemcollection.getsearchresultsasstream`; SharePoint list-stream calls loaded list content. The company SharePoint search page submitted `POST /searchservice/api/v2/query` for `File` and `People`, with `GET /search/api/v1/suggestions` for suggestions and separate init/configuration calls. The response envelope carried Search result sets, but these private routes are distinct from Graph `driveItem` search. See the [route map above](#microsoft-365-search-capture-and-source-route-map-sharepoint-and-onedrive-2026-10-10) for counts and route details.

The SharePoint search capture also contains 24 HTTP 200 `GET /api/v1/documents/searchpreview` requests returning JPEG images. In both relevant HARs, all 24 preview requests' `uniqueId`, `siteId`, `webId`, and `listId` values matched those four fields on a captured Search result `Source` record. This proves item-level association between the preview and a search result, but not that a click caused each request (the page may preload previews), not file-content opening, and not a mapping to Graph drive/item IDs. For agent-directed expansion, retain the direct Graph drive/item identity and `webUrl` when a Graph result provides them.

The SharePoint client source adds two browser-side paging contracts: a scoped File request builder uses `From=0`, `Size=5` and a 10-minute client cache keyed by search text; a Lists Home provider requests `Size=24`, advances `From` by 24 while `MoreResultsAvailable` is true, and parses the first result set. The source callers were not matched one-to-one to HAR requests; in particular, the captured company SharePoint result submissions used `/searchservice/api/v2/query`, while these builders target `/search/api/v2/query`. Only offset-zero requests appeared in the capture set, so the next-page path is source-established, not capture-verified. The result parser retains SharePoint navigation fields such as `AccessUrl`, `SPWebUrl`, `SpoUniqueId`, `SiteId`, `WebId`, `ListId` and `ParentLink`; this still does not map the browser item to Graph drive/item identifiers. The preview source builds an image request with a `ClientScenario` header and returns a blob URL, not document content. See the [route map above](#microsoft-365-search-capture-and-source-route-map-sharepoint-and-onedrive-2026-10-10).

The same Graph Search API transport is used in the Outlook investigation for `message`, `event`, and `person`, but the `driveItem` entity is the file-search path. Teams' captured `search/api/v2/query` is a separate search service. Teams may display files in its Files results category, but the captured evidence does not establish that category's implementation is the same as the tested SharePoint/OneDrive Graph query.

Search route limits and request notes are in the [coverage review](#microsoft-365-search-api-coverage-review-2026-10-10) and the [route map](#microsoft-365-search-capture-and-source-route-map-sharepoint-and-onedrive-2026-10-10) above. Search API `driveItem` results are not evidence that every SharePoint library, OneDrive item, attachment, or Teams file is indexed and accessible.

| Shared mechanism | Products / data | How the workflows relate |
| --- | --- | --- |
| `POST /v1.0/drives/{driveId}/items/{itemId}/preview` | OneDrive/SharePoint DriveItem preview. | Four HTTP 200 POSTs plus two successful OPTIONS preflights across three items whose drive/item identifiers were also returned in MCPS meeting-resource metadata. This is an item-level preview route, not Graph Search; file-search result ID equivalence remains unproven. |

Outlook mail already has a direct message-ID and conversation-ID expansion path. SharePoint/OneDrive hits should retain drive/item identity and a web URL when available so the selected file can be opened or fetched by its own route. These are related context workflows but use different resource identities and APIs.

| Content | Graph Search API entity | What it searches | Status in this investigation |
| --- | --- | --- | --- |
| OneDrive and company SharePoint files | `driveItem` | Files/folders within content the signed-in user can read, across OneDrive and SharePoint. | Implemented in the read-only SharePoint connector. Filename/content known hits, selected-item hydration/download, and two explicit pages succeeded for the tested locations. Exhaustive recall and minimum permissions remain unverified. |

## Official references

- [Microsoft Search files across OneDrive and SharePoint](https://learn.microsoft.com/en-us/graph/search-concept-files)
- [Microsoft Graph Search API overview and paging](https://learn.microsoft.com/en-us/graph/api/resources/search-api-overview?view=graph-rest-1.0)
- [SearchRequest resource](https://learn.microsoft.com/en-us/graph/api/resources/searchrequest?view=graph-rest-1.0)
- [Get a driveItem](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0)
- [Download driveItem content](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
