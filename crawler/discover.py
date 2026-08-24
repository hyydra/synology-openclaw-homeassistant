"""Command-line entry point for bounded source discovery runs."""

from __future__ import annotations

import argparse


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def _archive_depth(value: str) -> int:
    parsed = int(value)
    if parsed < 0 or parsed > 3:
        raise argparse.ArgumentTypeError("archive depth must be between 0 and 3")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with conservative, explicitly bounded defaults."""
    parser = argparse.ArgumentParser(description="Discover historical Hungarian/Pécs web sources.")
    parser.add_argument("--seed-file", default="crawler/seeds/pecs.txt")
    parser.add_argument("--max-pages", type=_positive_int, default=500)
    parser.add_argument("--max-depth", type=_positive_int, default=2)
    parser.add_argument("--domain-limit", type=_positive_int, default=50)
    parser.add_argument("--cdx-validate", action="store_true")
    parser.add_argument("--discover-orphans", action="store_true")
    parser.add_argument("--archive-depth", type=_archive_depth, default=1)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse crawler CLI arguments without starting a crawl."""
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate arguments now; crawl orchestration is added in later plan tasks."""
    parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
