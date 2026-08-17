"""Physical-design convergence report parsing and export tools."""

from .models import RunSummary
from .parser import ParseError, discover_run_directories, parse_run, parse_runs

__all__ = [
    "ParseError",
    "RunSummary",
    "discover_run_directories",
    "parse_run",
    "parse_runs",
]

__version__ = "1.0.0"

