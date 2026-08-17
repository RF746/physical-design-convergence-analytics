from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pd_convergence.parser import ParseError, discover_run_directories, parse_run, parse_runs


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = REPOSITORY_ROOT / "sample_data"


class ParserTests(unittest.TestCase):
    def test_discovers_three_synthetic_runs(self) -> None:
        run_directories = discover_run_directories(SAMPLE_DATA)
        self.assertEqual(3, len(run_directories))
        self.assertEqual("run_001_baseline", run_directories[0].name)

    def test_parses_complete_convergence_series(self) -> None:
        summaries = parse_runs(SAMPLE_DATA)

        self.assertEqual(
            ["run_001_baseline", "run_002_timing_fix", "run_003_closed"],
            [summary.run_id for summary in summaries],
        )
        self.assertAlmostEqual(-0.34, summaries[0].wns_ns)
        self.assertAlmostEqual(-5.72, summaries[0].tns_ns)
        self.assertEqual(6, summaries[0].drc_violations)
        self.assertAlmostEqual(0.07, summaries[-1].wns_ns)
        self.assertAlmostEqual(18600.0, summaries[-1].area_um2)
        self.assertEqual(0, summaries[-1].drc_violations)

    def test_normalizes_picoseconds_to_nanoseconds(self) -> None:
        summary = parse_run(SAMPLE_DATA / "run_002_timing_fix")
        self.assertAlmostEqual(0.2, summary.clock_skew_ns)
        self.assertAlmostEqual(0.78, summary.insertion_delay_ns)

    def test_normalizes_parenthesized_picoseconds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            report = SAMPLE_DATA / "run_003_closed" / "openroad_summary.rpt"
            text = report.read_text(encoding="utf-8").replace(
                "Max clock skew = 0.190 ns", "Max clock skew (ps): 190"
            )
            (run_dir / "physical.rpt").write_text(text, encoding="utf-8")
            (run_dir / "timing.rpt").write_text(
                "WNS (ps): 70\nTNS (ps): 0\n", encoding="utf-8"
            )

            summary = parse_run(run_dir)
            self.assertAlmostEqual(0.07, summary.wns_ns)
            self.assertAlmostEqual(0.19, summary.clock_skew_ns)

    def test_rejects_conflicting_units(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            report = SAMPLE_DATA / "run_003_closed" / "openroad_summary.rpt"
            (run_dir / "physical.rpt").write_text(
                report.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (run_dir / "timing.rpt").write_text(
                "WNS (ps): 70 ns\nTNS: 0 ns\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ParseError, "Conflicting units"):
                parse_run(run_dir)

    def test_rejects_conflicting_metric_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            report = SAMPLE_DATA / "run_003_closed" / "openroad_summary.rpt"
            timing = SAMPLE_DATA / "run_003_closed" / "opensta_summary.rpt"
            (run_dir / "physical.rpt").write_text(
                report.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (run_dir / "timing_a.rpt").write_text(
                timing.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (run_dir / "timing_b.rpt").write_text(
                "WNS: -0.12 ns\nTNS: 0 ns\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ParseError, "Conflicting values for wns_ns"):
                parse_run(run_dir)

    def test_rejects_invalid_scalar_bounds(self) -> None:
        replacements = {
            "Total DRC violations = 0": "Total DRC violations = 2.5",
            "Total cell area: 18,600.0 um^2": "Total cell area: -1 um^2",
            "Core utilization: 40.2%": "Core utilization: 101%",
        }
        expected_messages = ["non-negative integer", "greater than zero", "between 0 and 100"]
        source = SAMPLE_DATA / "run_003_closed" / "openroad_summary.rpt"
        timing = SAMPLE_DATA / "run_003_closed" / "opensta_summary.rpt"

        for (old, new), expected in zip(replacements.items(), expected_messages):
            with self.subTest(replacement=new), tempfile.TemporaryDirectory() as temporary_directory:
                run_dir = Path(temporary_directory)
                (run_dir / "physical.rpt").write_text(
                    source.read_text(encoding="utf-8").replace(old, new),
                    encoding="utf-8",
                )
                (run_dir / "timing.rpt").write_text(
                    timing.read_text(encoding="utf-8"), encoding="utf-8"
                )
                with self.assertRaisesRegex(ParseError, expected):
                    parse_run(run_dir)

    def test_preserves_configuration_metadata(self) -> None:
        summary = parse_run(SAMPLE_DATA / "run_003_closed")
        self.assertEqual("closed", summary.config["flow_variant"])
        self.assertEqual(10.0, summary.config["clock_period_ns"])

    def test_reports_missing_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            (run_dir / "partial.rpt").write_text("WNS: -0.1 ns\n", encoding="utf-8")

            with self.assertRaisesRegex(ParseError, "Missing metrics"):
                parse_run(run_dir)

    def test_rejects_non_object_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            source = SAMPLE_DATA / "run_003_closed" / "openroad_summary.rpt"
            timing = SAMPLE_DATA / "run_003_closed" / "opensta_summary.rpt"
            (run_dir / "physical.rpt").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            (run_dir / "timing.rpt").write_text(timing.read_text(encoding="utf-8"), encoding="utf-8")
            (run_dir / "config.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

            with self.assertRaisesRegex(ParseError, "Expected a JSON object"):
                parse_run(run_dir)


if __name__ == "__main__":
    unittest.main()
