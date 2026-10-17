from __future__ import annotations

import json

import httpx
import pytest

from sharepoint_connector.domain.errors import InvalidRequest
from sharepoint_connector.remote.graph import Graph
from sharepoint_connector.service.files import Files
from tests.fakes import FakeRepository, FakeTokens


@pytest.mark.asyncio
async def test_graph_search_maps_resource_ids_not_search_hit_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1.0/search/query"
        assert request.headers["authorization"] == "Bearer synthetic-token"
        body = json.loads(request.content)
        assert body["requests"] == [
            {
                "entityTypes": ["driveItem"],
                "query": {"queryString": "needle"},
                "from": 25,
                "size": 25,
            }
        ]
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "hitsContainers": [
                            {
                                "total": 80,
                                "moreResultsAvailable": True,
                                "hits": [
                                    {
                                        "hitId": "not-the-drive-item-id",
                                        "rank": 2.5,
                                        "summary": "a matching excerpt",
                                        "resource": {
                                            "id": "resource-item-id",
                                            "name": "report.docx",
                                            "size": 123,
                                            "webUrl": "https://tenant.sharepoint.com/report.docx",
                                            "file": {"mimeType": "application/vnd.test-document"},
                                            "parentReference": {
                                                "driveId": "resource-drive-id",
                                                "id": "parent-id",
                                                "path": "/drives/resource-drive-id/root:/Reports",
                                            },
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        page = await Graph(FakeTokens(), client=client).search_drive_items("needle", offset=25, page_size=25)
    assert page.total_hits == 80
    assert page.more_results_available
    assert page.next_offset == 50
    assert page.hits[0].item_id == "resource-item-id"
    assert page.hits[0].drive_id == "resource-drive-id"
    assert page.hits[0].item_id != "not-the-drive-item-id"
    assert page.hits[0].summary == "a matching excerpt"


@pytest.mark.asyncio
async def test_scoped_search_adds_path_constraint_and_returns_original_query() -> None:
    repository = FakeRepository()
    page = await Files(repository).search_files(
        "annual report",
        scope_url="https://tenant.sharepoint.com/sites/finance/",
        page_size=12,
    )
    assert repository.query == 'annual report AND path:"https://tenant.sharepoint.com/sites/finance"'
    assert repository.offset == 0
    assert repository.page_size == 12
    assert page.query == "annual report"
    assert page.scope_url == "https://tenant.sharepoint.com/sites/finance"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"query": ""},
        {"query": "   "},
        {},
        {"query": "x", "cursor": "not a cursor"},
        {"cursor": "A" * 3000},
        {"cursor": "bm90IGpzb24"},
        {"query": "x", "page_size": 201},
        {"query": "x", "scope_url": "https://example.invalid/site"},
        {"query": "x", "scope_url": "https://tenant.sharepoint.com/site?q=wide"},
        {"query": "x", "scope_url": "https://tenant.sharepoint.com:bad/site"},
        {"query": "x", "scope_url": "https://tenant.sharepoint.com:444/site"},
        {"query": "x OR name:other", "scope_url": "https://tenant.sharepoint.com/site"},
    ],
)
async def test_search_rejects_invalid_or_widenable_inputs(kwargs) -> None:
    with pytest.raises(InvalidRequest):
        await Files(FakeRepository()).search_files(**kwargs)


@pytest.mark.asyncio
async def test_search_has_no_next_cursor_when_graph_says_last_page() -> None:
    repository = FakeRepository()
    page = await Files(repository).search_files("needle")
    assert page.next_cursor is None
    assert page.more_results_available is False


@pytest.mark.asyncio
async def test_next_cursor_carries_the_query_scope_and_position_to_the_next_page() -> None:
    repository = FakeRepository()
    repository.total_results = 5
    files = Files(repository)
    scope = "https://tenant.sharepoint.com/sites/finance"

    first = await files.search_files("annual report", scope_url=scope, page_size=2)
    second = await files.search_files(cursor=first.next_cursor)
    last = await files.search_files(cursor=second.next_cursor)

    assert first.next_cursor is not None and second.next_cursor is not None
    assert (repository.offset, repository.page_size) == (4, 2)
    assert second.query == "annual report" and second.scope_url == scope
    assert repository.query == 'annual report AND path:"https://tenant.sharepoint.com/sites/finance"'
    assert last.more_results_available is False and last.next_cursor is None
    assert "offset" not in second.model_dump()


@pytest.mark.asyncio
async def test_a_cursor_is_used_alone_and_must_be_one_we_issued() -> None:
    files = Files(FakeRepository())
    with pytest.raises(InvalidRequest):
        await files.search_files("again", cursor="anything")
    with pytest.raises(InvalidRequest):
        await files.search_files(cursor="this is not one of ours")
