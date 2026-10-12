from __future__ import annotations

import httpx
import pytest

from sharepoint_connector.remote.graph import Graph
from tests.fakes import FakeTokens


@pytest.mark.asyncio
async def test_metadata_uses_encoded_resource_references_and_maps_parent() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.raw_path.startswith(b"/v1.0/drives/drive%2Fvalue/items/item%21value?")
        assert b"%24select=" in request.url.raw_path
        return httpx.Response(
            200,
            json={
                "id": "actual-item-id",
                "name": "budget.docx",
                "webUrl": "https://tenant.sharepoint.com/budget.docx",
                "size": 240,
                "file": {
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                },
                "createdDateTime": "2026-01-01T00:00:00Z",
                "lastModifiedDateTime": "2026-02-01T00:00:00Z",
                "parentReference": {"id": "parent", "path": "/drive/root:/Shared"},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        item = await Graph(FakeTokens(), client=client).get_drive_item("drive/value", "item!value")
    assert item.item_id == "actual-item-id"
    assert item.drive_id == "drive/value"
    assert item.parent_path == "/drive/root:/Shared"
    assert item.size_bytes == 240
    assert item.is_folder is False
