from __future__ import annotations

from typing import Any

from m365_auth import AccessToken

from sharepoint_connector.domain.models import FileMetadata, RemoteSearchPage, SearchHit


class FakeAccessToken(AccessToken):
    def __init__(self, profile: str, claims: dict[str, str]) -> None:
        super().__init__(profile, "synthetic-token", "test", None)
        object.__setattr__(self, "_synthetic_claims", claims)

    def claims(self) -> dict[str, Any]:
        return self._synthetic_claims


class FakeTokens:
    def __init__(self, tenant: str = "tenant-a", object_id: str = "user-a") -> None:
        self.tenant = tenant
        self.object_id = object_id

    def get_token(
        self,
        profile: str,
        *,
        force_refresh: bool = False,
        claims_challenge: str | None = None,
    ) -> AccessToken:
        claims = {"tid": self.tenant, "oid": self.object_id, "upn": "person@example.invalid"}
        return FakeAccessToken(profile, claims)


class FakeRepository:
    def __init__(self) -> None:
        self.query: str | None = None
        self.offset = 0
        self.page_size = 0
        self.drive_id = "drive-id"
        self.item_id = "item-id"
        self.metadata = FileMetadata(
            drive_id=self.drive_id,
            item_id=self.item_id,
            name="sample.txt",
            size_bytes=4,
            content_type="text/plain",
        )
        self.content = b"data"
        self.fail_download: Exception | None = None
        self.total_results = 1  # how many results the fake search has; more than one makes pages

    async def search_drive_items(self, query: str, *, offset: int, page_size: int) -> RemoteSearchPage:
        self.query = query
        self.offset = offset
        self.page_size = page_size
        more = offset + page_size < self.total_results
        return RemoteSearchPage(
            total_hits=self.total_results,
            more_results_available=more,
            next_offset=offset + page_size if more else None,
            hits=[
                SearchHit(
                    drive_id=self.drive_id,
                    item_id=self.item_id,
                    name="sample.txt",
                    summary="sample snippet",
                    rank=1,
                )
            ],
        )

    async def get_drive_item(self, drive_id: str, item_id: str) -> FileMetadata:
        self.drive_id, self.item_id = drive_id, item_id
        return self.metadata.model_copy(update={"drive_id": drive_id, "item_id": item_id})

    async def download_drive_item(self, drive_id: str, item_id: str, destination: Any, *, max_bytes: int):
        if self.fail_download:
            raise self.fail_download
        destination.write(self.content)
        return "text/plain", len(self.content)
