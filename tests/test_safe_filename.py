from __future__ import annotations

import pytest

from sharepoint_connector.service.files import _safe_filename  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.pdf", "report.pdf"),
        ("CON", "_CON"),
        ("con.backup.txt", "_con.backup.txt"),
        ("COM0.log", "_COM0.log"),
        ("COM¹.txt", "_COM¹.txt"),
        ("lpt³", "_lpt³"),
        ("COM10.txt", "COM10.txt"),
    ],
)
def test_windows_device_names_are_made_portable(name: str, expected: str) -> None:
    assert _safe_filename(name) == expected
