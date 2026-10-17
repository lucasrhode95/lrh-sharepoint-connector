"""Microsoft Graph Search, driveItem metadata and content adapter.

This module owns Graph route spelling, request bodies and wire response mapping. Search results keep
resource-level drive/item IDs; the distinct Microsoft Search hitId is never used as a driveItem ID.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import time
from collections.abc import Awaitable, Callable
from email.utils import parsedate_to_datetime
from typing import Any, BinaryIO, NoReturn, Protocol
from urllib.parse import quote, urlsplit

import httpx
from m365_auth import AccessToken, Account, AccountMismatch, AuthenticationRequired

from sharepoint_connector import config
from sharepoint_connector.domain.errors import (
    DownloadLimitExceeded,
    NotFound,
    PermissionDenied,
    Throttled,
    Upstream,
)
from sharepoint_connector.domain.models import FileMetadata, RemoteSearchPage, SearchHit

RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})
MAX_ATTEMPTS = 3
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024
MAX_ERROR_TEXT = 120
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
PREAUTH_HOST_SUFFIXES = ("sharepoint.com", "sharepoint-df.com", "1drv.com")


class TokenSource(Protocol):
    def get_token(self, profile: str) -> AccessToken: ...


class Graph:
    def __init__(
        self,
        tokens: TokenSource,
        *,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        expected_account_fingerprint: str | None = None,
    ) -> None:
        self._tokens = tokens
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=15.0), follow_redirects=False
        )
        self._owns_client = client is None
        self._limit = asyncio.Semaphore(4)
        self._sleep = sleep
        self._expected_account_fingerprint = expected_account_fingerprint

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search_drive_items(self, query: str, *, offset: int, page_size: int) -> RemoteSearchPage:
        payload = await self._json(
            "POST",
            "/search/query",
            body={
                "requests": [
                    {
                        "entityTypes": ["driveItem"],
                        "query": {"queryString": query},
                        "from": offset,
                        "size": page_size,
                    }
                ]
            },
        )
        values = _list(payload.get("value"))
        containers: list[dict[str, Any]] = []
        for result in values:
            if isinstance(result, dict):
                containers.extend(
                    item for item in _list(result.get("hitsContainers")) if isinstance(item, dict)
                )

        hits: list[SearchHit] = []
        totals: list[int] = []
        more = False
        for container in containers:
            total = container.get("total")
            if isinstance(total, int) and total >= 0:
                totals.append(total)
            more = more or container.get("moreResultsAvailable") is True
            for raw_hit in _list(container.get("hits")):
                if not isinstance(raw_hit, dict):
                    continue
                resource = raw_hit.get("resource")
                resource = resource if isinstance(resource, dict) else {}
                parent = resource.get("parentReference")
                parent = parent if isinstance(parent, dict) else {}
                file = resource.get("file")
                file = file if isinstance(file, dict) else {}
                hits.append(
                    SearchHit(
                        drive_id=_optional_string(parent.get("driveId")),
                        item_id=_optional_string(resource.get("id")),
                        name=_optional_string(resource.get("name")) or "Unnamed item",
                        web_url=_optional_string(resource.get("webUrl")),
                        content_type=_optional_string(file.get("mimeType")),
                        size_bytes=_optional_int(resource.get("size")),
                        created_at=_optional_string(resource.get("createdDateTime")),
                        modified_at=_optional_string(resource.get("lastModifiedDateTime")),
                        parent_id=_optional_string(parent.get("id")),
                        parent_path=_optional_string(parent.get("path")),
                        is_folder=isinstance(resource.get("folder"), dict),
                        rank=_optional_number(raw_hit.get("rank")),
                        summary=_optional_string(raw_hit.get("summary")),
                    )
                )

        next_offset = offset + page_size if more and offset + page_size <= config.MAX_OFFSET else None
        return RemoteSearchPage(
            total_hits=max(totals) if totals else None,
            more_results_available=more,
            next_offset=next_offset,
            hits=hits,
            coverage_note=(
                "Microsoft Search is relevance-ranked and limited to files the signed-in account can read; "
                "it does not guarantee exhaustive recall."
                if next_offset is not None or not more
                else "The result offset limit was reached. Microsoft Search is relevance-ranked and does not "
                "guarantee exhaustive recall."
            ),
        )

    async def get_drive_item(self, drive_id: str, item_id: str) -> FileMetadata:
        payload = await self._json(
            "GET",
            _item_path(drive_id, item_id),
            params={
                "$select": (
                    "id,name,webUrl,size,file,folder,createdDateTime,lastModifiedDateTime,parentReference"
                )
            },
        )
        return _metadata(payload, drive_id=drive_id)

    async def download_drive_item(
        self, drive_id: str, item_id: str, destination: BinaryIO, *, max_bytes: int
    ) -> tuple[str | None, int]:
        path = _item_path(drive_id, item_id) + "/content"
        for attempt in range(MAX_ATTEMPTS):
            token = self._access_token()
            request = self._client.build_request(
                "GET", config.GRAPH_ROOT + path, headers={"Authorization": f"Bearer {token}"}
            )
            response: httpx.Response | None = None
            try:
                response = await self._send(request)
                if response.status_code in RETRYABLE_STATUSES and attempt + 1 < MAX_ATTEMPTS:
                    delay = _retry_delay(response)
                    await response.aclose()
                    response = None
                    await self._sleep(delay)
                    destination.seek(0)
                    destination.truncate()
                    continue
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    await response.aclose()
                    response = None
                    if not location:
                        raise Upstream("Graph returned a download redirect without a location.")
                    response = await self._open_preauthenticated(location)
                if response is None:
                    raise AssertionError("Download response was closed before content streaming.")
                if response.status_code != 200:
                    raw, _ = await _read_body(response, MAX_ERROR_BYTES)
                    error = _graph_error(response.status_code, raw)
                    await response.aclose()
                    response = None
                    _raise_status(error[0], error[1])
                result = await self._copy_response(response, destination, max_bytes)
                self._access_token()  # Fail a selected download if the shared account switched mid-transfer.
                return result
            except httpx.RequestError as exc:
                if response is not None:
                    await response.aclose()
                destination.seek(0)
                destination.truncate()
                if attempt + 1 < MAX_ATTEMPTS:
                    await self._sleep(float(attempt + 1))
                    continue
                raise Upstream("The selected file download failed.") from exc
            finally:
                if response is not None:
                    await response.aclose()
        raise Upstream("The selected file download failed.")

    async def _json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not path.startswith("/") or path.startswith("//"):
            raise AssertionError("Graph adapters must use a relative API path.")
        url = config.GRAPH_ROOT + path
        if params:
            url += "?" + "&".join(f"{quote(key)}={quote(value)}" for key, value in params.items())
        for attempt in range(MAX_ATTEMPTS):
            token = self._access_token()
            request = self._client.build_request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                json=body,
            )
            raw = b""
            retry_delay: float | None = None
            try:
                # The request limit covers the whole exchange, body included: a streamed body counts too.
                async with self._limit:
                    response = await self._client.send(request, stream=True)
                    try:
                        if response.status_code in RETRYABLE_STATUSES and attempt + 1 < MAX_ATTEMPTS:
                            retry_delay = _retry_delay(response)
                        elif response.status_code < 200 or response.status_code >= 300:
                            error_body, _ = await _read_body(response, MAX_ERROR_BYTES)
                            status, code = _graph_error(response.status_code, error_body)
                            _raise_status(status, code)
                        else:
                            raw, complete = await _read_body(response, MAX_JSON_BYTES)
                            if not complete:
                                raise Upstream("Microsoft Graph returned an oversized JSON response.")
                    finally:
                        await response.aclose()
            except httpx.RequestError as exc:  # includes a connection that drops while its body is read
                if attempt + 1 < MAX_ATTEMPTS:
                    await self._sleep(float(attempt + 1))
                    continue
                raise Upstream("Microsoft Graph could not be reached.") from exc
            if retry_delay is not None:
                await self._sleep(retry_delay)
                continue
            try:
                payload = json.loads(raw)
            except ValueError as exc:
                raise Upstream("Microsoft Graph returned invalid JSON.") from exc
            if not isinstance(payload, dict):
                raise Upstream("Microsoft Graph returned an unexpected JSON shape.")
            # A sign-in can replace the shared cache while Graph is servicing this request.
            # Do not return data fetched under a token that no longer belongs to this context.
            self._access_token()
            return payload
        raise Upstream("Microsoft Graph could not be reached.")

    def _access_token(self) -> str:
        token = self._tokens.get_token(config.GRAPH_PROFILE)
        if self._expected_account_fingerprint is not None:
            claims = token.claims()
            tenant_id, object_id = claims.get("tid"), claims.get("oid")
            if not tenant_id or not object_id:
                raise AccountMismatch(
                    "The active Microsoft account identity is unavailable; retry the request."
                )
            account = Account(tenant_id=str(tenant_id), object_id=str(object_id), username=None)
            if account.fingerprint != self._expected_account_fingerprint:
                raise AccountMismatch("The active Microsoft account changed; retry the request.")
        return token.value

    async def _send(self, request: httpx.Request) -> httpx.Response:
        async with self._limit:
            return await self._client.send(request, stream=True)

    async def _open_preauthenticated(self, url: str) -> httpx.Response:
        current = _validate_preauthenticated_url(url)
        for _ in range(4):
            response = await self._send(self._client.build_request("GET", current))
            if response.status_code not in REDIRECT_STATUSES:
                if response.status_code < 200 or response.status_code >= 300:
                    raw, _ = await _read_body(response, MAX_ERROR_BYTES)
                    error = _graph_error(response.status_code, raw)
                    await response.aclose()
                    _raise_status(error[0], error[1])
                return response
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise Upstream("The file host returned an invalid redirect.")
            current = _validate_preauthenticated_url(location)
        raise Upstream("The file host returned too many redirects.")

    async def _copy_response(
        self, response: httpx.Response, destination: BinaryIO, max_bytes: int
    ) -> tuple[str | None, int]:
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    raise DownloadLimitExceeded(max_bytes)
            except ValueError:
                pass
        total = 0
        try:
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise DownloadLimitExceeded(max_bytes)
                destination.write(chunk)
            destination.flush()
        except BaseException:
            destination.seek(0)
            destination.truncate()
            raise
        return response.headers.get("content-type"), total


def _item_path(drive_id: str, item_id: str) -> str:
    return f"/drives/{quote(drive_id, safe='')}/items/{quote(item_id, safe='')}"


def _metadata(item: dict[str, Any], *, drive_id: str) -> FileMetadata:
    item_id = _optional_string(item.get("id"))
    name = _optional_string(item.get("name"))
    if not item_id or not name:
        raise Upstream("Microsoft Graph returned incomplete driveItem metadata.")
    parent = item.get("parentReference")
    parent = parent if isinstance(parent, dict) else {}
    file = item.get("file")
    file = file if isinstance(file, dict) else {}
    return FileMetadata(
        drive_id=drive_id,
        item_id=item_id,
        name=name,
        web_url=_optional_string(item.get("webUrl")),
        content_type=_optional_string(file.get("mimeType")),
        size_bytes=_optional_int(item.get("size")),
        created_at=_optional_string(item.get("createdDateTime")),
        modified_at=_optional_string(item.get("lastModifiedDateTime")),
        parent_id=_optional_string(parent.get("id")),
        parent_path=_optional_string(parent.get("path")),
        is_folder=isinstance(item.get("folder"), dict),
    )


def _validate_preauthenticated_url(value: str) -> str:
    parts = urlsplit(value)
    host = (parts.hostname or "").lower().rstrip(".")
    try:
        port = parts.port
    except ValueError as exc:
        raise Upstream("Graph returned a download URL outside the trusted HTTPS boundary.") from exc
    if (
        parts.scheme != "https"
        or not host
        or parts.username is not None
        or parts.password is not None
        or port not in (None, 443)
    ):
        raise Upstream("Graph returned a download URL outside the trusted HTTPS boundary.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise Upstream("Graph returned a download URL outside the trusted HTTPS boundary.")
    if not any(host == suffix or host.endswith("." + suffix) for suffix in PREAUTH_HOST_SUFFIXES):
        raise Upstream("Graph returned a download URL outside the trusted Microsoft file hosts.")
    return value


def _graph_error(status: int, body: bytes) -> tuple[int, str | None]:
    code = None
    try:
        data = json.loads(body)
    except ValueError:
        data = None
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        code = error["code"][:MAX_ERROR_TEXT]
    return status, code


async def _read_body(response: httpx.Response, limit: int) -> tuple[bytes, bool]:
    """The response body, read in chunks and stopped once it passes ``limit`` bytes. The flag says
    whether the body was read to its end; a caller that needs all of it refuses the response otherwise."""
    body = bytearray()
    async for chunk in response.aiter_bytes():
        if len(body) + len(chunk) > limit:
            body.extend(chunk[: limit - len(body)])
            return bytes(body), False
        body.extend(chunk)
    return bytes(body), True


def _raise_status(status: int, code: str | None) -> NoReturn:
    detail = f" (Graph code {code})" if code else ""
    if status in (401, 403):
        if status == 401:
            raise AuthenticationRequired(
                f"Microsoft Graph rejected the current profile{detail}.",
                command=f"{config.CLI_NAME} auth",
            )
        raise PermissionDenied(f"Microsoft Graph denied access{detail}.")
    if status == 404:
        raise NotFound("The selected drive item was not found or is no longer readable.")
    if status == 429:
        raise Throttled("Microsoft Graph is throttling file access; wait and retry.")
    raise Upstream(f"Microsoft Graph returned HTTP {status}{detail}.")


def _retry_delay(response: httpx.Response) -> float:
    value = response.headers.get("retry-after", "")
    try:
        return min(30.0, max(0.0, float(value)))
    except ValueError:
        try:
            date = parsedate_to_datetime(value).timestamp()
            return min(30.0, max(0.0, date - time.time()))
        except (TypeError, ValueError, OverflowError):
            return 1.0


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _optional_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
