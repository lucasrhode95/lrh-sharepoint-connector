from sharepoint_connector.__main__ import build_parser


def test_cli_has_one_data_surface_and_explicit_shared_sign_out() -> None:
    parser = build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")
    assert set(subparsers.choices) == {"auth", "status", "mcp"}
    args = parser.parse_args(["auth", "--sign-out"])
    assert args.sign_out is True
