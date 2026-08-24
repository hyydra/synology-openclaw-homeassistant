from crawler.discover import parse_args


def test_cli_defaults_are_conservative():
    args = parse_args([])
    assert args.max_pages == 500
    assert args.max_depth == 2
    assert args.domain_limit == 50
    assert args.archive_depth == 1
    assert args.cdx_validate is False
    assert args.discover_orphans is False


def test_cli_rejects_invalid_bounds():
    for argv in (["--max-pages", "0"], ["--domain-limit", "0"], ["--archive-depth", "4"], ["--archive-depth", "-1"]):
        try:
            parse_args(list(argv))
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError(f"arguments must be rejected: {argv}")
