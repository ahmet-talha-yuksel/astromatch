# Marius Hills measured-only regional candidate

`features.json` contains T-03, `moon_marius_hills_regional`, as a separate
measured-only export. The curated release and its original quality decisions
remain unchanged. This candidate is not merged into the default engine inputs
and does not automatically promote Marius for scoring.

The source is the already acquired official LOLA LDEM_128 height crop with its
matching LDEC_128 observation counts. Original labels and retrieval evidence
are in `processing/raw/marius_hills/`; source URL, access date, DEM SHA-256 and
counts SHA-256 are embedded in the record. LDEM's native 0.5 m DN scale is
applied once. The source and analysis sphere is 1737400 m.

The analysis is the same 50×50 km LAEA window with 1000 m cells. Source bins
with counts <=0 are removed before area-average reprojection. NoData remains
NoData. `measured_only_planefit_v1` supplies the original six terrain metrics;
`quality.morphology` describes the three additional measured-only descriptors.
The heightmap represents this measured-only window; PNGs do not supply metrics.

All nine fields have plain numeric controls in `features_interpolated` and
absolute/relative checks in `measurement_support.sensitivity`. The thresholds
are <=15% relative difference OR the per-feature absolute tolerance; morphology
uses HI 0.02, roughness ratio 0.05 and curvature 0.01 km^-1. These are engineering
sensitivity tolerances, not independent accuracy evidence. All nine comparisons
currently pass, while the prior lunar approval remains closed. Measurement
support, effective NoData and explicit reasons remain available for review.

This is regional terrain context. A 1000 m analysis does not resolve the
approximately 50 m pit entrance.

Reproduce from the repo root without downloading data:

```sh
processing/.venv/bin/python -m processing.scripts.measured_mars marius
```
