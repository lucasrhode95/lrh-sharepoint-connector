from pathlib import Path

from m365_auth import CacheStatus, ProfileStatus

from sharepoint_connector import __main__ as cli
from sharepoint_connector.__main__ import build_parser


def test_cli_has_one_data_surface_and_explicit_shared_sign_out() -> None:
    parser = build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")
    assert set(subparsers.choices) == {"auth", "status", "mcp"}
    args = parser.parse_args(["auth", "--sign-out"])
    assert args.sign_out is True


def test_status_reports_client_cache_and_resource_token_separately(monkeypatch, capsys) -> None:
    class Provider:
        def __init__(self, **_: object) -> None:
            pass

        def status(self) -> CacheStatus:
            profiles = (
                ProfileStatus("teams.spaces", "teams", (), "chat", True, 2_000_000_000),
                ProfileStatus("teams.csa", "teams", (), "catalog", True, None),
            )
            return CacheStatus("encrypted", Path("cache"), True, (), profiles)

    monkeypatch.setattr(cli, "TokenProvider", Provider)

    assert cli.main(["status"]) == 0
    output = capsys.readouterr().out
    assert "[teams.spaces] client credential cached; access token expires 2033-05-18T03:33:20+00:00" in output
    assert "[teams.csa] client credential cached; access token expires not cached" in output
