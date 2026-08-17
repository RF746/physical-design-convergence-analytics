"""CSV and JSON exporters for parsed convergence summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import RunSummary


BASE_COLUMNS = [
    "run_id",
    "wns_ns",
    "tns_ns",
    "area_um2",
    "utilization_pct",
    "drc_violations",
    "clock_skew_ns",
    "insertion_delay_ns",
]


def _csv_safe(value: Any) -> Any:
    """Prevent spreadsheet programs from interpreting config text as formulas."""

    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _prepare_output(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def write_json(summaries: Iterable[RunSummary], path: str | Path) -> Path:
    """Write summaries as an indented JSON array."""

    output_path = _prepare_output(path)
    records = [summary.to_record() for summary in summaries]
    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return output_path


def _flatten_record(summary: RunSummary, config_keys: list[str]) -> dict[str, Any]:
    record = summary.to_record()
    config = record.pop("config")
    for key in config_keys:
        value = config.get(key, "")
        flattened = (
            json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
        )
        record[f"config_{key}"] = _csv_safe(flattened)
    return record


def write_csv(summaries: Iterable[RunSummary], path: str | Path) -> Path:
    """Write summaries as CSV, flattening configuration keys with a prefix."""

    summary_list = list(summaries)
    output_path = _prepare_output(path)
    config_keys = sorted({key for summary in summary_list for key in summary.config})
    fieldnames = BASE_COLUMNS + [f"config_{key}" for key in config_keys]

    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summary_list:
            writer.writerow(_flatten_record(summary, config_keys))
    return output_path
