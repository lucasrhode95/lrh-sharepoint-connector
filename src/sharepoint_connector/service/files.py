"""File search, metadata hydration and user-selected bounded downloads."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

from sharepoint_connector import config
from sharepoint_connector.domain.errors import DownloadLimitExceeded, InvalidRequest
from sharepoint_connector.domain.models import FileMetadata, SavedFile, SearchPage
from sharepoint_connector.remote.ports import FileRepository

_SCOPE_QUERY_OPERATOR = re.compile(r'\b(?:AND|OR|NOT)\b|["():*]', re.IGNORECASE)
_BAD_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_NAME = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.IGNORECASE)


class Files:
    """Public service entry point; validates MCP input before calling the repository port."""

    def __init__(
        self,
        repository: FileRepository,
        *,
        output_home: Path | None = None,
        account_fingerprint: str = "active",
    ) -> None:
        self._repository = repository
        self._output_home = output_home
        self._account_fingerprint = account_fingerprint

    async def search_files(
        self,
        query: str,
        *,
        offset: int = 0,
        page_size: int = config.DEFAULT_PAGE_SIZE,
        scope_url: str | None = None,
    ) -> SearchPage:
        query = _validate_query(query)
        offset = _validate_integer("offset", offset, 0, config.MAX_OFFSET)
        page_size = _validate_integer("page_size", page_size, 1, config.MAX_PAGE_SIZE)
        normalized_scope = _validate_scope(scope_url) if scope_url is not None else None
        query_string = query
        if normalized_scope is not None:
            if _SCOPE_QUERY_OPERATOR.search(query):
                raise InvalidRequest(
                    "Scoped search accepts plain terms only; KQL operators are disabled so the location "
                    "constraint cannot be widened."
                )
            query_string = f'{query} AND path:"{normalized_scope}"'
        page = await self._repository.search_drive_items(query_string, offset=offset, page_size=page_size)
        page.query = query
        page.scope_url = normalized_scope
        return page

    async def get_file_metadata(self, drive_id: str, item_id: str) -> FileMetadata:
        drive_id = _validate_reference(drive_id, "drive_id")
        item_id = _validate_reference(item_id, "item_id")
        return await self._repository.get_drive_item(drive_id, item_id)

    async def download_file(
        self,
        drive_id: str,
        item_id: str,
        *,
        max_bytes: int = config.DEFAULT_DOWNLOAD_BYTES,
    ) -> SavedFile:
        drive_id = _validate_reference(drive_id, "drive_id")
        item_id = _validate_reference(item_id, "item_id")
        max_bytes = _validate_integer("max_bytes", max_bytes, 1, config.MAX_DOWNLOAD_BYTES)
        metadata = await self._repository.get_drive_item(drive_id, item_id)
        if metadata.is_folder:
            raise InvalidRequest("Folders cannot be downloaded.")
        if metadata.size_bytes is not None and metadata.size_bytes > max_bytes:
            raise DownloadLimitExceeded(max_bytes)
        output_dir = self._download_directory()
        output_dir.mkdir(parents=True, exist_ok=True)
        path, file = _create_exclusive(output_dir, _safe_filename(metadata.name))
        try:
            content_type, size = await self._repository.download_drive_item(
                drive_id, item_id, file, max_bytes=max_bytes
            )
            file.close()
            return SavedFile(path=path, filename=path.name, content_type=content_type, size_bytes=size)
        except BaseException:
            file.close()
            path.unlink(missing_ok=True)
            raise

    def _download_directory(self) -> Path:
        base = self._output_home if self._output_home is not None else config.data_dir()
        return base / "downloads" / self._account_fingerprint


def _validate_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise InvalidRequest("query must contain at least one search term.")
    if len(query) > 512 or any(ord(char) < 32 for char in query):
        raise InvalidRequest("query must be at most 512 characters and contain no control characters.")
    return query.strip()


def _validate_integer(name: str, value: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise InvalidRequest(f"{name} must be an integer from {minimum} through {maximum}.")
    return value


def _validate_reference(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise InvalidRequest(f"{name} must be a non-empty driveItem reference.")
    if any(ord(char) < 32 for char in value):
        raise InvalidRequest(f"{name} contains an invalid control character.")
    return value


def _validate_scope(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise InvalidRequest("scope_url must be an absolute SharePoint or OneDrive URL.")
    parts = urlsplit(value)
    host = (parts.hostname or "").lower().rstrip(".")
    try:
        port = parts.port
    except ValueError as exc:
        raise InvalidRequest("scope_url must use the default HTTPS port.") from exc
    if (
        parts.scheme != "https"
        or not host
        or parts.username is not None
        or parts.password is not None
        or port not in (None, 443)
        or parts.query
        or parts.fragment
        or any(char in value for char in ('"', "\\"))
        or any(ord(char) < 32 for char in value)
    ):
        raise InvalidRequest(
            "scope_url must be an absolute HTTPS SharePoint or OneDrive URL without query or fragment."
        )
    if not any(host == suffix or host.endswith("." + suffix) for suffix in ("sharepoint.com", "1drv.com")):
        raise InvalidRequest("scope_url must use a SharePoint or OneDrive host.")
    return value.rstrip("/")


def _safe_filename(value: str) -> str:
    basename = value.replace("/", "\\").rsplit("\\", 1)[-1].strip().rstrip(".")
    cleaned = _BAD_FILENAME.sub("_", basename)
    if cleaned in ("", ".", ".."):
        cleaned = "download"
    if _RESERVED_WINDOWS_NAME.match(cleaned):
        cleaned = "_" + cleaned
    return cleaned[:180]


def _create_exclusive(directory: Path, filename: str) -> tuple[Path, BinaryIO]:
    stem, suffix = Path(filename).stem, Path(filename).suffix
    for index in range(10_000):
        name = filename if index == 0 else f"{stem} ({index}){suffix}"
        path = directory / name
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        return path, os.fdopen(descriptor, "wb")
    raise InvalidRequest("Could not create a unique local download filename.")
