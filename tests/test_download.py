from __future__ import annotations

import httpx
import pytest

from sharepoint_connector.domain.errors import DownloadLimitExceeded, Upstream
from sharepoint_connector.remote.graph import Graph
from sharepoint_connector.service.files import Files
from tests.fakes import FakeRepository, FakeTokens


def graph_item(name: str = "sample.txt", size: int = 4) -> dict[str, object]:
    return {
        "id": "item-id",
        "name": name,
        "size": size,
        "file": {"mimeType": "text/plain"},
    }


@pytest.mark.asyncio
async def test_download_never_forwards_graph_bearer_to_preauth_host(tmp_path) -> None:
    methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.url.host == "graph.microsoft.com":
            assert request.headers.get("authorization") == "Bearer synthetic-token"
            if request.url.path.endswith("/content"):
                return httpx.Response(
                    302, headers={"Location": "https://tenant.sharepoint.com/preauth?sig=temporary"}
                )
            return httpx.Response(200, json=graph_item())
        assert request.url.host == "tenant.sharepoint.com"
        assert request.headers.get("authorization") is None
        return httpx.Response(200, content=b"data", headers={"Content-Type": "text/plain"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        files = Files(Graph(FakeTokens(), client=client), output_home=tmp_path, account_fingerprint="acct")
        saved = await files.download_file("drive-id", "item-id")
    assert saved.path.read_bytes() == b"data"
    assert saved.path.parent.name == "acct"
    assert saved.content_type == "text/plain"
    assert methods == ["GET", "GET", "GET"]


@pytest.mark.asyncio
async def test_unsafe_download_redirect_is_rejected_and_partial_file_removed(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/content"):
            return httpx.Response(302, headers={"Location": "https://attacker.invalid/steal"})
        return httpx.Response(200, json=graph_item())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        files = Files(Graph(FakeTokens(), client=client), output_home=tmp_path)
        with pytest.raises(Upstream, match="trusted"):
            await files.download_file("drive-id", "item-id")
    assert all(not path.is_file() for path in tmp_path.rglob("*"))


@pytest.mark.asyncio
async def test_oversized_stream_is_removed_after_limit_error(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/content"):
            return httpx.Response(302, headers={"Location": "https://tenant.sharepoint.com/preauth"})
        if request.url.host == "graph.microsoft.com":
            return httpx.Response(200, json=graph_item(size=0))
        return httpx.Response(200, content=b"12345")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        files = Files(Graph(FakeTokens(), client=client), output_home=tmp_path)
        with pytest.raises(DownloadLimitExceeded):
            await files.download_file("drive-id", "item-id", max_bytes=4)
    assert all(not path.is_file() for path in tmp_path.rglob("*"))


@pytest.mark.asyncio
async def test_duplicate_downloads_use_exclusive_names(tmp_path) -> None:
    repository = FakeRepository()
    files = Files(repository, output_home=tmp_path)
    first = await files.download_file("drive", "item")
    second = await files.download_file("drive", "item")
    assert first.filename == "sample.txt"
    assert second.filename == "sample (1).txt"
    assert first.path.read_bytes() == second.path.read_bytes() == b"data"
