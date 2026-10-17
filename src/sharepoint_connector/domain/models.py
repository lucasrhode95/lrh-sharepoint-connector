"""Typed, compact results returned through MCP and the command-line status tools."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class FileMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drive_id: str
    item_id: str
    name: str
    web_url: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None
    modified_at: str | None = None
    parent_id: str | None = None
    parent_path: str | None = None
    is_folder: bool = False


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drive_id: str | None = None
    item_id: str | None = None
    name: str
    web_url: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None
    modified_at: str | None = None
    parent_id: str | None = None
    parent_path: str | None = None
    is_folder: bool = False
    rank: float | None = None
    summary: str | None = None

    @property
    def can_hydrate(self) -> bool:
        return bool(self.drive_id and self.item_id)


class RemoteSearchPage(BaseModel):
    """One page as Microsoft Search returned it. Internal: the service hands out a cursor, never an offset."""

    model_config = ConfigDict(extra="ignore")

    total_hits: int | None = None
    more_results_available: bool
    next_offset: int | None = None
    hits: list[SearchHit]
    coverage_note: str = (
        "Microsoft Search is relevance-ranked and limited to files the signed-in account can read; "
        "it does not guarantee exhaustive recall."
    )


class SearchPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: str
    scope_url: str | None = None
    page_size: int
    total_hits: int | None = None
    more_results_available: bool
    next_cursor: str | None = None
    hits: list[SearchHit]
    coverage_note: str = (
        "Microsoft Search is relevance-ranked and limited to files the signed-in account can read; "
        "it does not guarantee exhaustive recall."
    )


class SavedFile(BaseModel):
    path: Path
    filename: str
    content_type: str | None
    size_bytes: int
