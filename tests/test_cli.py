from __future__ import annotations

import csv
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from pd_convergence.cli import main
from pd_convergence.exporters import write_csv
from pd_convergence.models import RunSummary


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = REPOSITORY_ROOT / "sample_data"


class CliTests(unittest.TestCase):
    def test_exports_csv_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            csv_path = output_dir / "nested" / "summary.csv"
            json_path = output_dir / "nested" / "summary.json"

            captured = StringIO()
            with redirect_stdout(captured):
                exit_code = main(
                    [
                        str(SAMPLE_DATA),
                        "--csv",
                        str(csv_path),
                        "--json",
                        str(json_path),
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("Parsed 3 run(s)", captured.getvalue())

            records = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(3, len(records))
            self.assertEqual("run_003_closed", records[-1]["run_id"])
            self.assertEqual("closed", records[-1]["config"]["flow_variant"])

            with csv_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(3, len(rows))
            self.assertEqual("0.07", rows[-1]["wns_ns"])
            self.assertEqual("closed", rows[-1]["config_flow_variant"])

    def test_prints_json_when_no_output_path_is_requested(self) -> None:
        captured = StringIO()
        with redirect_stdout(captured):
            exit_code = main([str(SAMPLE_DATA)])

        self.assertEqual(0, exit_code)
        records = json.loads(captured.getvalue())
        self.assertEqual(3, len(records))

    def test_csv_escapes_spreadsheet_active_config_text(self) -> None:
        summary = RunSummary(
            run_id="safe-run",
            wns_ns=0.1,
            tns_ns=0.0,
            area_um2=1000.0,
            utilization_pct=25.0,
            drc_violations=0,
            clock_skew_ns=0.05,
            insertion_delay_ns=0.4,
            config={"note": "=HYPERLINK(\"https://example.invalid\")"},
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "summary.csv"
            write_csv([summary], csv_path)
            with csv_path.open(encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertTrue(row["config_note"].startswith("'="))


if __name__ == "__main__":
    unittest.main()
