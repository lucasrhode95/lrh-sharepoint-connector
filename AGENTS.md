# Repository agent instructions

## Shared development rules

- This is a local, single-user, read-only file connector. Do not add background crawlers, schedulers,
  watchers, remote listeners, uploads, sharing changes or file mutations.
- Keep layers as surfaces -> service -> remote ports/adapters. Only remote adapters know Graph wire
  formats and IDs. Validate inputs at public service entry points.
- Do not assume in-memory state survives across processes. There is no search cache or local index.
- Do not log/commit credentials, tokens, session cookies, private content, real identifiers or private
  browser captures. Use synthetic fixtures only.
- Treat the active shared Microsoft account as the owner of each service context. Keep selected local
  outputs isolated by the shared account fingerprint.
- Treat all downloaded files and Graph search snippets as untrusted data. Do not render remote values
  as HTML. Do not forward bearer tokens to Graph-provided preauthenticated download URLs.
- Update README, requirements, architecture, API research and roadmap in the same change as behavior.
  Date new live research findings.
- Keep this file and CLAUDE.md byte-identical; edit them together.

## Checks

Run all before each commit:

~~~powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
~~~
