from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from sharepoint_connector.domain.errors import Upstream
from sharepoint_connector.remote import graph
from tests.fakes import FakeTokens

CHUNK = b"x" * (1024 * 1024)
CHUNKS = 64  # 64 MiB, far above the JSON cap, so an unbounded read would show up in the count


async def test_an_oversized_json_response_is_refused_once_it_passes_the_cap() -> None:
    produced = 0

    async def body() -> AsyncIterator[bytes]:
        nonlocal produced
        for _ in range(CHUNKS):
            produced += len(CHUNK)
            yield CHUNK

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body())

    async def no_sleep(_: float) -> None:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = graph.Graph(FakeTokens(), client=client, sleep=no_sleep)
        try:
            await adapter._json("GET", "/me")
        except Upstream as exc:
            assert "oversized" in str(exc)
        else:
            raise AssertionError("an oversized response was accepted")
    assert produced <= graph.MAX_JSON_BYTES + len(CHUNK)
