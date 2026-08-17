"""Parsers for OpenROAD/OpenSTA-style text reports.

The parser intentionally targets a small, documented interchange surface
rather than attempting to cover every tool version. It accepts common metric
labels and normalizes time units to nanoseconds.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from .models import RunSummary


REPORT_SUFFIXES = {".rpt", ".report", ".txt"}
NUMBER = r"[-+]?(?:\d+(?:,\d{3})*(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"


class ParseError(ValueError):
    """Raised when a run cannot be converted into a complete summary."""


TIME_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "wns_ns": (
        re.compile(
            rf"\bWNS\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\bworst\s+negative\s+slack\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
    ),
    "tns_ns": (
        re.compile(
            rf"\bTNS\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\btotal\s+negative\s+slack\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
    ),
    "clock_skew_ns": (
        re.compile(
            rf"\b(?:maximum|max)\s+clock\s+skew\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\bclock\s+skew\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
    ),
    "insertion_delay_ns": (
        re.compile(
            rf"\b(?:clock\s+)?insertion\s+delay\b(?:\s*\((?P<label_unit>ps|ns)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>ps|ns)?",
            re.IGNORECASE,
        ),
    ),
}

SCALAR_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "area_um2": (
        re.compile(
            rf"\b(?:design|core|total\s+cell)\s+area\b(?:\s*\((?P<label_unit>um\^?2|[µμ]m²)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>um\^?2|[µμ]m²)?",
            re.IGNORECASE,
        ),
    ),
    "utilization_pct": (
        re.compile(
            rf"\b(?:core\s+)?utilization\b(?:\s*\((?P<label_unit>%|percent)\))?\s*[:=]?\s*(?P<value>{NUMBER})\s*(?P<suffix_unit>%|percent)?",
            re.IGNORECASE,
        ),
        re.compile(
            rf"(?P<value>{NUMBER})\s*%\s*utilization\b",
            re.IGNORECASE,
        ),
    ),
    "drc_violations": (
        re.compile(
            rf"\b(?:total\s+)?DRC\s+(?:violations|count)\b\s*[:=]?\s*(?P<value>{NUMBER})",
            re.IGNORECASE,
        ),
    ),
}


def _as_float(raw_value: str) -> float:
    return float(raw_value.replace(",", ""))


def _matches(text: str, patterns: Iterable[re.Pattern[str]]) -> list[re.Match[str]]:
    return [match for pattern in patterns for match in pattern.finditer(text)]


def _one_consistent_value(values: list[float], field_name: str) -> float | None:
    if not values:
        return None
    first = values[0]
    if any(not math.isclose(first, value, rel_tol=1e-9, abs_tol=1e-12) for value in values[1:]):
        rendered = ", ".join(f"{value:g}" for value in values)
        raise ParseError(f"Conflicting values for {field_name}: {rendered}")
    return first


def _resolved_unit(match: re.Match[str], field_name: str, default: str) -> str:
    groups = match.groupdict()
    label_unit = (groups.get("label_unit") or "").lower()
    suffix_unit = (groups.get("suffix_unit") or "").lower()
    if label_unit and suffix_unit and label_unit != suffix_unit:
        raise ParseError(
            f"Conflicting units for {field_name}: {label_unit} versus {suffix_unit}"
        )
    return suffix_unit or label_unit or default


def _extract_time_ns(
    text: str, patterns: Iterable[re.Pattern[str]], field_name: str
) -> float | None:
    values: list[float] = []
    for match in _matches(text, patterns):
        value = _as_float(match.group("value"))
        unit = _resolved_unit(match, field_name, "ns")
        normalized = value / 1000.0 if unit == "ps" else value
        if not math.isfinite(normalized):
            raise ParseError(f"Non-finite value for {field_name}")
        if field_name in {"clock_skew_ns", "insertion_delay_ns"} and normalized < 0:
            raise ParseError(f"{field_name} must be non-negative")
        values.append(normalized)
    return _one_consistent_value(values, field_name)


def _extract_scalar(
    text: str, patterns: Iterable[re.Pattern[str]], field_name: str
) -> float | int | None:
    values: list[float] = []
    for match in _matches(text, patterns):
        value = _as_float(match.group("value"))
        if not math.isfinite(value):
            raise ParseError(f"Non-finite value for {field_name}")
        if field_name in {"area_um2", "utilization_pct"}:
            default_unit = "um2" if field_name == "area_um2" else "%"
            _resolved_unit(match, field_name, default_unit)
        values.append(value)

    value = _one_consistent_value(values, field_name)
    if value is None:
        return None
    if field_name == "drc_violations":
        if value < 0 or not value.is_integer():
            raise ParseError("drc_violations must be a non-negative integer")
        return int(value)
    if field_name == "area_um2" and value <= 0:
        raise ParseError("area_um2 must be greater than zero")
    if field_name == "utilization_pct" and not 0 <= value <= 100:
        raise ParseError("utilization_pct must be between 0 and 100")
    return value


def _load_config(run_dir: Path) -> dict[str, Any]:
    config_path = run_dir / "config.json"
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON in {config_path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ParseError(f"Expected a JSON object in {config_path}")
    return data


def _report_paths(run_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in run_dir.iterdir()
        if path.is_file() and path.suffix.lower() in REPORT_SUFFIXES
    )


def discover_run_directories(root: str | Path) -> list[Path]:
    """Find directories under ``root`` that contain supported report files."""

    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {root_path}")

    candidates = {
        path.parent
        for path in root_path.rglob("*")
        if path.is_file() and path.suffix.lower() in REPORT_SUFFIXES
    }
    return sorted(candidates, key=lambda path: path.as_posix())


def parse_run(run_dir: str | Path) -> RunSummary:
    """Parse one run directory into normalized metrics."""

    run_path = Path(run_dir)
    reports = _report_paths(run_path)
    if not reports:
        raise ParseError(f"No supported report files found in {run_path}")

    text = "\n".join(path.read_text(encoding="utf-8") for path in reports)
    values: dict[str, float | int] = {}
    missing: list[str] = []

    for field_name, patterns in TIME_PATTERNS.items():
        value = _extract_time_ns(text, patterns, field_name)
        if value is None:
            missing.append(field_name)
        else:
            values[field_name] = value

    for field_name, patterns in SCALAR_PATTERNS.items():
        value = _extract_scalar(text, patterns, field_name)
        if value is None:
            missing.append(field_name)
            continue
        values[field_name] = value

    if missing:
        missing_display = ", ".join(sorted(missing))
        raise ParseError(f"Missing metrics in {run_path}: {missing_display}")

    config = _load_config(run_path)
    run_id = str(config.get("run_id") or run_path.name)

    return RunSummary(
        run_id=run_id,
        wns_ns=float(values["wns_ns"]),
        tns_ns=float(values["tns_ns"]),
        area_um2=float(values["area_um2"]),
        utilization_pct=float(values["utilization_pct"]),
        drc_violations=int(values["drc_violations"]),
        clock_skew_ns=float(values["clock_skew_ns"]),
        insertion_delay_ns=float(values["insertion_delay_ns"]),
        config=config,
    )


def parse_runs(root: str | Path) -> list[RunSummary]:
    """Discover and parse all runs below ``root``."""

    run_directories = discover_run_directories(root)
    if not run_directories:
        raise ParseError(f"No run directories found under {Path(root)}")

    summaries = [parse_run(run_dir) for run_dir in run_directories]
    run_ids = [summary.run_id for summary in summaries]
    if len(run_ids) != len(set(run_ids)):
        raise ParseError("Run identifiers must be unique")
    return summaries
