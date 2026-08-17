"""Command-line interface for convergence analytics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from . import __version__
from .exporters import write_csv, write_json
from .parser import ParseError, parse_runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pd-convergence",
        description=(
            "Parse OpenROAD/OpenSTA-style run reports and export normalized "
            "physical-design convergence metrics."
        ),
    )
    parser.add_argument("input", type=Path, help="Directory containing run folders")
    parser.add_argument("--csv", type=Path, help="Write a flattened CSV summary")
    parser.add_argument("--json", type=Path, help="Write a structured JSON summary")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        summaries = parse_runs(args.input)
    except (FileNotFoundError, NotADirectoryError, ParseError) as exc:
        parser.error(str(exc))

    outputs: list[str] = []
    if args.csv:
        outputs.append(f"CSV: {write_csv(summaries, args.csv)}")
    if args.json:
        outputs.append(f"JSON: {write_json(summaries, args.json)}")

    if outputs:
        print(f"Parsed {len(summaries)} run(s). " + " | ".join(outputs))
    else:
        print(json.dumps([summary.to_record() for summary in summaries], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

