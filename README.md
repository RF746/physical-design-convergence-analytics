# Physical Design Convergence Analytics

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small, dependency-free Python CLI that turns OpenROAD/OpenSTA-style text
reports into comparable CSV and JSON summaries. It demonstrates a repeatable
way to track timing, physical, clock, and configuration metrics across
implementation iterations.

> **Portfolio and data-safety notice:** this repository is a sanitized,
> independently implemented demonstration of the workflow. All bundled report
> text, configurations, design names, and measurements are synthetic. No
> proprietary reports, source code, netlists, layouts, or employer/customer
> data are included. See [Data provenance](DATA_PROVENANCE.md).

## What it measures

| Metric | Normalized output | Unit |
|---|---|---|
| Worst negative slack | `wns_ns` | ns |
| Total negative slack | `tns_ns` | ns |
| Design/core area | `area_um2` | µm² |
| Core utilization | `utilization_pct` | % |
| DRC violations | `drc_violations` | count |
| Maximum clock skew | `clock_skew_ns` | ns |
| Clock insertion delay | `insertion_delay_ns` | ns |
| Run settings and labels | `config` / `config_*` | mixed |

Time values reported in picoseconds are converted to nanoseconds. JSON keeps
configuration data nested; CSV flattens it into columns prefixed with
`config_`.

## Quick start

The project has no runtime dependencies beyond Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Parse the bundled synthetic samples:

```bash
pd-convergence sample_data \
  --csv build/convergence.csv \
  --json build/convergence.json
```

Or run the package module directly and print JSON to standard output:

```bash
python -m pd_convergence sample_data
```

The sample series is designed to produce this illustrative trend:

| Run | WNS (ns) | TNS (ns) | Area (µm²) | Util. (%) | DRC | Skew (ns) | Insertion (ns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `run_001_baseline` | -0.34 | -5.72 | 18,120 | 39.2 | 6 | 0.24 | 0.81 |
| `run_002_timing_fix` | -0.08 | -0.61 | 18,420 | 39.8 | 2 | 0.20 | 0.78 |
| `run_003_closed` | +0.07 | 0.00 | 18,600 | 40.2 | 0 | 0.19 | 0.76 |

These values are fabricated examples, not results from a production design.

## Expected input

Point the CLI at a directory containing one or more run folders:

```text
runs/
├── baseline/
│   ├── config.json
│   ├── openroad_summary.rpt
│   └── opensta_summary.rpt
└── optimized/
    ├── config.json
    ├── physical.report
    └── timing.txt
```

Supported report extensions are `.rpt`, `.report`, and `.txt`. A run may split
metrics across multiple report files; the parser combines all supported files
within that folder. Every run must provide all seven numeric metrics. Missing
metrics fail fast with a readable error instead of silently creating an
incomplete comparison.

Accepted labels include common summary variants such as:

```text
WNS (ns): -0.120
Total negative slack: -1.430 ns
Design area (um^2): 18420
Core utilization: 39.8%
Total DRC violations: 2
Maximum clock skew: 200 ps
Clock insertion delay: 0.780 ns
```

If a time label omits its unit, the parser assumes nanoseconds. `config.json`
is optional and must contain a JSON object when present. Its `run_id` value is
used as the run identifier; otherwise the folder name is used.

## Test and verify

```bash
python -m unittest discover -s tests -v
```

The test suite covers:

- discovery of multiple implementation runs;
- label variants and ps-to-ns normalization;
- complete convergence-series parsing;
- configuration preservation and CSV flattening;
- CSV/JSON CLI exports; and
- readable failures for missing metrics or invalid configuration data.

GitHub Actions repeats the suite on Python 3.10, 3.11, and 3.12 and exercises
the installed CLI.

## Repository layout

```text
.
├── .github/workflows/ci.yml
├── sample_data/                  # Explicitly synthetic demonstration reports
├── src/pd_convergence/
│   ├── cli.py                    # Argument parsing and orchestration
│   ├── exporters.py              # Stable CSV and JSON schemas
│   ├── models.py                 # Normalized run data model
│   └── parser.py                 # Discovery, extraction, validation, units
├── tests/
├── DATA_PROVENANCE.md
├── SECURITY.md
└── pyproject.toml
```

## Design choices

- **Standard library only:** simple to review and run in constrained
  environments.
- **Explicit units:** normalized field names make comparisons unambiguous.
- **Fail-fast validation:** a row is never presented as complete when a
  required metric is missing.
- **Preserved configuration:** implementation settings remain beside measured
  results for traceable comparisons.
- **Narrow parsing surface:** the supported labels are documented and tested;
  tool-specific additions can be introduced as focused patterns and fixtures.

## Extending the parser

To support another report spelling, add a compiled pattern to
`TIME_PATTERNS` or `SCALAR_PATTERNS` in `src/pd_convergence/parser.py`, then add
a synthetic fixture and assertion. Do not commit confidential tool output or
design information when adding examples.

## License

Released under the [MIT License](LICENSE).
