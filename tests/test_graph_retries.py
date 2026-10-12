from __future__ import annotations

import httpx
import pytest

from sharepoint_connector.domain.errors import Throttled
from sharepoint_connector.remote.graph import Graph
from tests.fakes import FakeTokens


@pytest.mark.asyncio
async def test_search_retries_throttled_read_and_honors_retry_after() -> None:
    calls = 0
    delays: list[float] = []

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"value": []})

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        page = await Graph(FakeTokens(), client=client, sleep=sleep).search_drive_items(
            "needle", offset=0, page_size=5
        )
    assert calls == 2
    assert delays == [0.0]
    assert page.hits == []


@pytest.mark.asyncio
async def test_exhausted_throttled_read_is_reported_without_unbounded_retries() -> None:
    calls = 0
    delays: list[float] = []

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "0"})

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(Throttled):
            await Graph(FakeTokens(), client=client, sleep=sleep).search_drive_items(
                "needle", offset=0, page_size=5
            )
    assert calls == 3
    assert delays == [0.0, 0.0]
