"""CLI for shared authentication, status and the stdio MCP server."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from m365_auth import AuthenticationRequired, TokenProvider, check_profiles, status_lines

from sharepoint_connector import config
from sharepoint_connector.domain.errors import ConnectorError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_AUTH_REQUIRED = 2


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "auth":
            return _auth(args.sign_out)
        if args.command == "status":
            return _status(args.check)
        if args.command == "mcp":
            from sharepoint_connector.logs import configure_app_logging
            from sharepoint_connector.surfaces.mcp_main import serve_mcp

            configure_app_logging("mcp")  # file only: stdout belongs to the MCP protocol from here on
            serve_mcp()
            return EXIT_OK
        raise AssertionError(f"Unknown command: {args.command}")
    except AuthenticationRequired as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_AUTH_REQUIRED
    except ConnectorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        return 130


def _auth(sign_out: bool) -> int:
    provider = TokenProvider(login_command=f"{config.CLI_NAME} auth")
    if sign_out:
        existed = provider.sign_out()
        print("Signed out of the shared Microsoft account." if existed else "No shared sign-in to clear.")
        return EXIT_OK
    results = provider.bootstrap(show=lambda message: print(f"\n{message}\n", flush=True))
    for result in results:
        if result.ready:
            print(f"[{result.profile}] Ready.")
        else:
            print(f"[{result.profile}] Not ready: {result.error}", file=sys.stderr)
    if all(result.ready for result in results):
        return EXIT_OK
    return EXIT_AUTH_REQUIRED


def _status(check: bool) -> int:
    provider = TokenProvider(login_command=f"{config.CLI_NAME} auth")
    checks = check_profiles(provider) if check else {}
    for line in status_lines(provider, checks):
        print(line)
    graph = checks.get(config.GRAPH_PROFILE)
    return EXIT_AUTH_REQUIRED if graph is not None and not graph["ok"] else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=config.CLI_NAME, description="Read-only OneDrive and SharePoint file connector."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    auth = commands.add_parser("auth", help="Prepare or sign out of the shared Microsoft 365 profiles.")
    auth.add_argument(
        "--sign-out", action="store_true", help="Clear authentication for all three connectors."
    )
    status = commands.add_parser("status", help="Show cached client credentials and Graph token state.")
    status.add_argument("--check", action="store_true", help="Also acquire the Graph token silently.")
    commands.add_parser("mcp", help="Run the stdio MCP server.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
