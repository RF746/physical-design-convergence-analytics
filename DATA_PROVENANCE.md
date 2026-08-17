# Data provenance and confidentiality

## Scope

This repository is a public portfolio implementation created to demonstrate a
general physical-design report normalization workflow. It is not a publication
of reports or scripts from any workplace, customer engagement, foundry
relationship, tapeout, or restricted academic project.

## Bundled data

All files under `sample_data/` were written expressly for this repository and
are synthetic. Their metric values were manually selected to form an
easy-to-understand convergence sequence for parser tests and documentation.
They do not describe an actual chip or correlate to a proprietary design.

The bundled data contains no:

- proprietary netlist, RTL, layout, or constraint content;
- real block, product, customer, supplier, or employee names;
- internal paths, hostnames, ticket identifiers, or repository links;
- foundry-restricted rules, libraries, or process data; or
- production PPA, timing, DRC, clock, or configuration results.

## Implementation provenance

The Python package is an independent, sanitized implementation using only the
publicly recognizable idea of labeled EDA summary metrics. It parses a narrow,
documented set of OpenROAD/OpenSTA-style labels and does not reproduce a
private report schema or internal automation framework.

## Adding data safely

Before committing another fixture:

1. Generate it specifically for public demonstration.
2. Remove company, customer, product, user, machine, network, and path names.
3. Replace measurements and configurations with intentionally synthetic values.
4. Confirm the file contains no source design, constraint, library, or layout
   material.
5. Label the fixture as synthetic in the file itself and in documentation.

When in doubt, do not commit the data. A minimal fabricated fixture is enough
to test a parser behavior.

