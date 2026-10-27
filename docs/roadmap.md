# SharePoint connector roadmap

Open work only. What the connector must do, its ownership boundaries and settled decisions are in the
[requirements](requirements.md); how it is built is in the [architecture](architecture.md); dated live
evidence is in the [research record](api-research.md). Delete an item once it is done.

Work is split by what it needs: **implementation** is code still to write; **live verification** checks
something on a real tenant before it is relied on, and becomes implementation only if a check fails.

Snapshot **2026-10-27**.

## Implementation

The read-only connector in the [requirements](requirements.md) is built. The items below extend it and stay
tenant-agnostic: the connector discovers a library's structure at runtime and never interprets a column by
its name. Each item adds its capability to [requirements §3](requirements.md#3-read-only-capabilities) in the
same change.

### Custom library columns in metadata

Hydrated metadata returns only driveItem fields, so values a library keeps in its own columns (for example a
document number, revision or owner) are reachable only by downloading the file.

- Read the item's list item fields and the library's column definitions at runtime.
- Return every custom column generically: display name, internal name, column type and value.
- Exclude SharePoint system columns by default, with an option to include them.
- Normalize values by column type only: person to name and email, managed metadata to label and term ID,
  lookup to value and ID, choice and date as typed. Never map a column name to a meaning.
- Done when the same call returns the custom columns of any library, whatever its column set.

### Filter a library by any column

- Filter one library's items by `{column: value}` on any column, using Graph list item filtering.
- When Graph refuses the filter because the column is not indexed, return that refusal; never fall back to a
  partial scan or an unfiltered result.
- Page with the same opaque cursor contract as search.

### List a folder or library

- List one folder's or library's children, read-only and paged with the opaque cursor contract.
- This gives complete enumeration of one location, which ranked search does not promise.

### User-defined site aliases

- Let a user map short names to site, library or folder URLs in their own configuration, and accept an
  alias wherever a scope URL is accepted.
- Ship no aliases; the configuration format is documented, the names are the user's.

## Live verification

Checks against a real tenant. Each needs the user's authorization for the live read it makes; record the
dated result in the research record.

### Minimum permissions

The tested account's existing file and site grants are broader than the shared profile's requested
`Mail.Read` and `User.Read` ([research, "Permissions"](api-research.md#permissions)),
so the live checks prove that account's access, not the scopes the connector needs. Repeat search,
metadata and download on an account without those extra grants, and record which scope each needs.

### Fresh-account consent

The shared sign-in was verified on an account that had already consented. Check a new account's consent
for `outlook.graph` before relying on it for file access.

### List item and folder permissions

Before the column, filter and listing items are relied on, check which delegated scopes list item fields,
column definitions, list item filtering and folder children need on the shared `outlook.graph` profile, and
whether they need consent beyond what search, metadata and download use.

### Search latency

One second-page search took 24.9 s while an immediate repeat took 2.5 s without `Retry-After`
([research, 2026-10-11](api-research.md#paging-and-latency)).
Measure a few paged searches before treating it as throttling or tuning page sizes.
