from __future__ import annotations

from sharepoint_connector import config
from sharepoint_connector.service.files import Files
from tests.fakes import FakeRepository


async def test_a_cursor_too_long_to_pass_back_is_not_issued_and_the_page_says_why() -> None:
    repository = FakeRepository()
    repository.total_results = 100
    files = Files(repository)
    scope = "https://contoso.sharepoint.com/sites/" + "a" * 1000
    page = await files.search_files("x" * 512, scope_url=scope, page_size=25)
    assert page.more_results_available is True
    assert page.next_cursor is None
    assert "too long to continue paging" in page.coverage_note
    assert len(page.hits) == 1


async def test_a_cursor_that_fits_is_issued_and_passes_back() -> None:
    repository = FakeRepository()
    repository.total_results = 100
    files = Files(repository)
    page = await files.search_files("needle", page_size=25)
    assert page.next_cursor is not None
    assert len(page.next_cursor) <= config.MAX_CURSOR_CHARS
    await files.search_files(cursor=page.next_cursor)
    assert repository.offset == 25
