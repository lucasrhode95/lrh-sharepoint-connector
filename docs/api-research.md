# SharePoint and OneDrive file research

Dated evidence that Microsoft's documentation does not give: what a live account returned, and the
browser's private routes. What Graph documents (the Search API and its `driveItem` entity, KQL `path:`
filters, paging limits, `driveItem` reads and content downloads with their redirect) is in the
[official references](#official-references) and is not repeated here. Results are account-, tenant-,
permission- and index-specific; re-check them before relying on them elsewhere. No file names, markers,
identifiers, URLs or content were retained.

## Graph file search, live (2026-10-11)

Synthetic files in personal OneDrive and in a shared company SharePoint library, read with the shared
`outlook.graph` profile through `POST /v1.0/search/query` with `entityTypes=["driveItem"]`.

### Results and indexing

- A filename term and a unique content-only term each returned the expected file, one hit per query, in
  both locations. A random negative marker returned zero.
- The shared-library file was missing from the first search after upload and appeared after more indexing
  time. This shows indexing lag in one example; it is not an indexing-time guarantee.

### Hydration and download

- `resource.parentReference.driveId` plus `resource.id` from a hit hydrated the item
  (`GET /v1.0/drives/{drive-id}/items/{item-id}`) and downloaded its content; the 13 synthetic bytes
  matched the local file in both locations. The hit's `hitId` was not used as an item id.

### Path scope

- A KQL `path:` constraint on a representative OneDrive parent URL and on a representative shared-library
  parent URL each returned the known hit. Other URL forms and other tenants are untested; a zero result for
  an arbitrary path does not show the syntax is unsupported.

### Paging and latency

- Five results at offset 0 and five distinct ones at offset 5, both with `moreResultsAvailable=true`.
- Single requests took about 0.5–1.8 s each (filename and content search, metadata, download, scoped
  search). One second-page request took 24.9 s; an immediate repeat took 2.5 s with HTTP 200 and no
  `Retry-After`. One outlier does not establish throttling or a latency distribution.

### Permissions

The profile requests Graph `Mail.Read` and `User.Read`, but the account's existing grants include broader
file and site permissions (Outlook connector research §3.1). The successful reads prove this account's
access, not the minimum scopes for file search, metadata or download.

## Browser routes (not used by the connector)

Captured 2026-10-10 from OneDrive and SharePoint web search, with the client source read 2026-10-11. These
routes work in the browser; nothing shows the connector could use them with its own sign-in, and none maps
its result identity to Graph drive and item ids.

### OneDrive Files search

- Submitted searches used Substrate `POST /search/api/v2/query` with `EntityRequests[].EntityType=File`
  (`From=0`, `Size=8`), and the SharePoint REST proxy
  `POST /_api/sp.searchresultitemcollection.getsearchresultsasstream?scenario=…` (`Size=25`), both answering
  `EntitySets[].ResultSets[].Results` with `Total` and `MoreResultsAvailable`. Observed result counts were
  8, 8, 13 and 25.
- `SP.List.GetListDataAsStream` and `RenderListDataAsStream` calls loaded list content; they are browsing,
  not search.
- Every captured request used offset 0; no next-page request appeared.

### SharePoint search page

- Submitted searches used `POST /searchservice/api/v2/query` with `File` and `People` entity requests; one
  of four answered with only `ApiVersion`, `SearchTerms` and `Instrumentation`.
- `GET /search/api/v1/suggestions` served suggestions; `/search/api/v2/init`, `/search/api/v1/userconfig`
  and `/search/api/v2/resources` are setup, and `/search/api/v1/events` is telemetry.
- `GET /api/v1/documents/searchpreview` (24 requests) returned JPEG images. Each request's `uniqueId`,
  `siteId`, `webId` and `listId` matched a result's `Source` record in the same capture, so a preview belongs
  to a result; the page may preload them, and they are images, not file content.

### Client source

- A scoped File request builder targets `/search/api/v2/query` with `From=0`, `Size=5`, and caches results
  for 10 minutes keyed by search text (a client cache, not server indexing delay).
- A Lists Home provider requests `Size=24` and advances `From` by 24 while `MoreResultsAvailable` is true,
  reading `EntitySets[0].ResultSets[0]`. Paging is therefore in source but was not seen on the wire.
- The result parser keeps `AccessUrl`, `SPWebUrl`, `SpoUniqueId`, `SiteId`, `WebId`, `ListId` and
  `ParentLink`; browser navigation uses `AccessUrl` or the site URL plus the unique id.
- The preview builder sends a `ClientScenario` header to a dynamic host and returns an image blob URL.
- These builders were not matched one-to-one to captured requests; the SharePoint page's captured
  submissions used `/searchservice/api/v2/query`, a different route.

## Official references

- [Search OneDrive and SharePoint content](https://learn.microsoft.com/en-us/graph/search-concept-files)
- [Search API overview and paging](https://learn.microsoft.com/en-us/graph/api/resources/search-api-overview?view=graph-rest-1.0)
- [SearchRequest resource](https://learn.microsoft.com/en-us/graph/api/resources/searchrequest?view=graph-rest-1.0)
- [Get a driveItem](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0)
- [Download driveItem content](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
