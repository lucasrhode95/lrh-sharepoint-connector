from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from sharepoint_connector.service.files import Files
from sharepoint_connector.surfaces.mcp_main import build_server
from tests.fakes import FakeRepository


class FakeContext:
    def __init__(self, files: Files) -> None:
        self._services = SimpleNamespace(files=files)

    async def services(self):
        return self._services


async def _call(server: FastMCP, name: str, **arguments: Any) -> Any:
    result = await server.call_tool(name, arguments)
    if isinstance(result, tuple):
        structured = result[1]
        return structured.get("result", structured) if isinstance(structured, dict) else structured
    if isinstance(result, dict):
        return result
    return json.loads(result[0].text)


@pytest.mark.asyncio
async def test_mcp_exposes_only_read_only_file_tools_and_uses_service_contract(tmp_path) -> None:
    repository = FakeRepository()
    files = Files(repository, output_home=tmp_path, account_fingerprint="acct")
    server = build_server(FakeContext(files))
    tools = {tool.name: tool for tool in await server.list_tools()}

    assert set(tools) == {"auth_status", "search_files", "get_file_metadata", "download_file"}
    assert all(tool.annotations and tool.annotations.readOnlyHint for tool in tools.values())
    assert all(tool.annotations and not tool.annotations.destructiveHint for tool in tools.values())
    assert "does not fetch file bytes" in (server.instructions or "")

    page = await _call(server, "search_files", query="needle", page_size=25)
    assert page["query"] == "needle"
    assert page["hits"][0]["drive_id"] == "drive-id"
    assert page["hits"][0]["item_id"] == "item-id"

    metadata = await _call(server, "get_file_metadata", drive_id="drive-id", item_id="item-id")
    assert metadata["name"] == "sample.txt"

    saved = await _call(server, "download_file", drive_id="drive-id", item_id="item-id")
    assert saved["filename"] == "sample.txt"
    assert (tmp_path / "downloads" / "acct" / "sample.txt").read_bytes() == b"data"
