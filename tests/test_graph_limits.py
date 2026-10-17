from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest

from sharepoint_connector.domain.errors import Upstream
from sharepoint_connector.remote import graph
from tests.fakes import FakeTokens

CHUNK = b"x" * (1024 * 1024)
CHUNKS = 64  # 64 MiB, far above the JSON cap, so an unbounded read would show up in the count


async def no_sleep(_: float) -> None:
    return None


async def test_an_oversized_json_response_is_refused_once_it_passes_the_cap() -> None:
    produced = 0

    async def body() -> AsyncIterator[bytes]:
        nonlocal produced
        for _ in range(CHUNKS):
            produced += len(CHUNK)
            yield CHUNK

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = graph.Graph(FakeTokens(), client=client, sleep=no_sleep)
        try:
            await adapter._json("GET", "/me")
        except Upstream as exc:
            assert "oversized" in str(exc)
        else:
            raise AssertionError("an oversized response was accepted")
    assert produced <= graph.MAX_JSON_BYTES + len(CHUNK)


async def test_a_connection_that_drops_mid_body_is_retried_then_reported_as_upstream() -> None:
    calls = 0

    async def dropping_body() -> AsyncIterator[bytes]:
        yield b'{"value": '
        raise httpx.ReadError("connection reset")

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=dropping_body())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = graph.Graph(FakeTokens(), client=client, sleep=no_sleep)
        with pytest.raises(Upstream, match="could not be reached"):
            await adapter._json("GET", "/me")
    assert calls == graph.MAX_ATTEMPTS


async def test_the_request_limit_holds_while_bodies_are_read() -> None:
    active = 0
    peak = 0
    release = asyncio.Event()

    async def slow_body() -> AsyncIterator[bytes]:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await release.wait()
            yield b'{"value": []}'
        finally:
            active -= 1

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=slow_body())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = graph.Graph(FakeTokens(), client=client, sleep=no_sleep)
        tasks = [asyncio.create_task(adapter._json("GET", "/me")) for _ in range(6)]
        await asyncio.sleep(0.05)
        assert (active, peak) == (4, 4)  # the adapter allows four requests at a time, bodies included
        release.set()
        results = await asyncio.gather(*tasks)
    assert results == [{"value": []}] * 6
