"""Ports consumed by domain services."""

from __future__ import annotations

from typing import BinaryIO, Protocol

from sharepoint_connector.domain.models import FileMetadata, SearchPage


class FileRepository(Protocol):
    async def search_drive_items(self, query: str, *, offset: int, page_size: int) -> SearchPage: ...

    async def get_drive_item(self, drive_id: str, item_id: str) -> FileMetadata: ...

    async def download_drive_item(
        self, drive_id: str, item_id: str, destination: BinaryIO, *, max_bytes: int
    ) -> tuple[str | None, int]: ...
