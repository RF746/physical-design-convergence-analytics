# Security policy

## Supported versions

Security fixes are applied to the latest version on the default branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability-reporting feature for this repository
when it is available. Do not disclose a suspected vulnerability, secret, or
sensitive file in a public issue.

Include:

- the affected version or commit;
- a concise reproduction;
- the expected and observed behavior; and
- the potential impact.

Avoid attaching proprietary EDA reports, netlists, layouts, credentials, or
other confidential material. A synthetic minimal reproduction is preferred.

## Data-handling expectations

The CLI reads local report files and writes only to output paths selected by
the caller. It has no network functionality and no runtime dependencies. Users
remain responsible for ensuring that their input and generated summaries are
approved for their environment and intended audience.

