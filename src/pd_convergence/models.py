"""Data models for normalized physical-design metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Normalized metrics for one implementation run.

    Time values are stored in nanoseconds, area in square micrometres, and
    utilization as a percentage. ``config`` preserves user-provided run
    metadata without interpreting tool-specific settings.
    """

    run_id: str
    wns_ns: float
    tns_ns: float
    area_um2: float
    utilization_pct: float
    drc_violations: int
    clock_skew_ns: float
    insertion_delay_ns: float
    config: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        """Return a JSON-ready record with explicit units."""

        return {
            "run_id": self.run_id,
            "wns_ns": self.wns_ns,
            "tns_ns": self.tns_ns,
            "area_um2": self.area_um2,
            "utilization_pct": self.utilization_pct,
            "drc_violations": self.drc_violations,
            "clock_skew_ns": self.clock_skew_ns,
            "insertion_delay_ns": self.insertion_delay_ns,
            "config": self.config,
        }

