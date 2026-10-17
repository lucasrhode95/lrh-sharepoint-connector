# SharePoint connector roadmap

Open work only. What the connector must do, its ownership boundaries and settled decisions are in the
[requirements](requirements.md); how it is built is in the [architecture](architecture.md); dated live
evidence is in the [research record](api-research.md). Delete an item once it is done.

Work is split by what it needs: **implementation** is code still to write; **live verification** checks
something on a real tenant before it is relied on, and becomes implementation only if a check fails.

Snapshot **2026-10-17**.

## Implementation

None open. The read-only connector in the [requirements](requirements.md) is built.

## Live verification

Checks against a real tenant. Each needs the user's authorization for the live read it makes; record the
dated result in the research record.

### Minimum permissions

The tested account's existing file and site grants are broader than the shared profile's requested
`Mail.Read` and `User.Read` ([research, "Permissions and shared auth"](api-research.md#permissions-and-shared-auth)),
so the live checks prove that account's access, not the scopes the connector needs. Repeat search,
metadata and download on an account without those extra grants, and record which scope each needs.

### Fresh-account consent

The shared sign-in was verified on an account that had already consented. Check a new account's consent
for `outlook.graph` before relying on it for file access.

### Search latency

One second-page search took 24.9 s while an immediate repeat took 2.5 s without `Retry-After`
([research log, 2026-10-11](api-research.md#2026-10-11--synthetic-onedrive-and-shared-library-validation)).
Measure a few paged searches before treating it as throttling or tuning page sizes.
