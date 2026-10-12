from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from m365_auth import Account, AccountMismatch

from sharepoint_connector.bootstrap import AppContext
from tests.fakes import FakeTokens


@pytest.mark.asyncio
async def test_services_and_stale_requests_follow_active_account(tmp_path: Path) -> None:
    tokens = FakeTokens()

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "hitsContainers": [
                            {
                                "hits": [
                                    {
                                        "resource": {
                                            "id": "item-id",
                                            "name": "sample.txt",
                                            "parentReference": {"driveId": "drive-id"},
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        context = AppContext(tokens=tokens, http_client=client, output_home=tmp_path)
        first = await context.services()
        tokens.tenant = "tenant-b"
        tokens.object_id = "person-b"
        second = await context.services()

        assert first.account.fingerprint != second.account.fingerprint
        assert first.files._download_directory() != second.files._download_directory()
        with pytest.raises(AccountMismatch, match="changed"):
            await first.files.search_files("needle")
        assert (await second.files.search_files("needle")).hits[0].name == "sample.txt"
        await context.aclose()


@pytest.mark.asyncio
async def test_graph_rejects_tokens_for_an_unbound_account() -> None:
    from sharepoint_connector.remote.graph import Graph

    tokens = FakeTokens(tenant="other-tenant")
    expected = Account("tenant-a", "user-a", None).fingerprint
    graph = Graph(tokens, expected_account_fingerprint=expected)
    with pytest.raises(AccountMismatch, match="changed"):
        await graph.search_drive_items("needle", offset=0, page_size=5)
    await graph.aclose()


@pytest.mark.asyncio
async def test_graph_rejects_account_switch_during_read() -> None:
    from sharepoint_connector.remote.graph import Graph

    tokens = FakeTokens()

    async def handler(_: httpx.Request) -> httpx.Response:
        tokens.tenant = "tenant-b"
        tokens.object_id = "person-b"
        return httpx.Response(200, json={"value": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        graph = Graph(
            tokens,
            client=client,
            expected_account_fingerprint=Account("tenant-a", "user-a", None).fingerprint,
        )
        with pytest.raises(AccountMismatch, match="changed"):
            await graph.search_drive_items("needle", offset=0, page_size=5)
