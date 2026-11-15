## Partial analog context data layer; blocked observations and consumer contract

Adds auxiliary Earth climate context and Moon thermal context with explicit null/reason coverage, plus source-reviewed qualitative profiles. No scoring feature, cell ID, region ID or eligibility value is changed. Only processing/ files are modified.

### Delivery

- A: 16 Earth site/scale records, 408 grid cells, seven annual context quantities. All observed values are null: Earthdata environment and netrc login were unavailable. The 192 unvalidated grid cells have cell_not_validated reasons. No 2021 monthly value is relabeled as a 2025 annual observation. Annual aggregation helpers and sanity checks are provided; authenticated extraction is still missing.
- B: three Moon record/scale contexts, all null with reasons. PDS South Polar Resource Product 1.0 metadata was opened. Its average is modeled at 2 cm depth, not a surface mean, and its ice-depth field is not a PSR mask. No unreliable conversion was performed.
- C: five target profiles and 16 Earth site/scale profiles; 13 sourced dimension records. All verified_by values remain null. Five Earth sites remain entirely unknown. PROFILE_REVIEW.md lists all claims/gaps and opened sources.

### Blocking integration and CI

CI is RED, not claimed green. Current engine extract_context fails on the required JSON-array warnings metadata, drops grid rows, and expects other lunar keys. Profile reader expects records rather than targets/earth_sites and requires non-null verified_by. These conflict with the requested data contract. engine/, backend/, frontend/ and workflow files were not changed. Coordinate consumer changes with the engine owner before merging. See processing/out/real/PROFILE_INTEGRATION.md.

### Validation

37 affected/new context/environment/grid-contract tests pass locally. Full processing suite: 156 passed, 1 skipped, 5 failed; those same five fail on a separate unchanged 865a534 baseline (baseline total 143 passed, 1 skipped, 6 failed). Historical snapshot comparisons project out only new context, while new semantic SHA256 tests verify every original record and Arrow value/ID is unchanged. Draft only; do not merge while acquisition and integration blockers remain.
