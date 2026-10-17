from __future__ import annotations

import logging

import pytest

from sharepoint_connector.surfaces.mcp_main import _logged


async def test_a_tool_call_logs_its_name_and_duration_but_not_its_arguments(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @_logged
    async def search_files(query: str) -> str:
        return "result"

    with caplog.at_level(logging.INFO):
        assert await search_files("secret search terms") == "result"

    messages = caplog.messages
    assert any(message.startswith("tool search_files completed in ") for message in messages)
    assert not any("secret search terms" in message for message in messages)


async def test_a_failing_tool_call_logs_a_warning_with_the_error_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @_logged
    async def get_file_metadata(drive_id: str) -> str:
        raise ValueError("detail that must not be logged")

    with caplog.at_level(logging.INFO), pytest.raises(ValueError):
        await get_file_metadata("drive-secret")

    warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
    assert any(message.startswith("tool get_file_metadata failed (ValueError) in ") for message in warnings)
    messages = caplog.messages
    assert not any("drive-secret" in message for message in messages)
    assert not any("must not be logged" in message for message in messages)
