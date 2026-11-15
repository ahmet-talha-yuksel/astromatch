# Why T-01 and T-03 have no validated matches

The active real inputs are `processing/out/real/features.json` followed by
`processing/out/mars_measured/features.json`. The latter wins for the regional
Jezero record. The readiness check requires a validated target resolution and
at least three non-null, comparable terrain features. No alternate real
`processing/out/**/features.json` currently meets those conditions for these
two targets. Mock records cannot be used in the real run.

| Target | Current blocker | Data-side completion route |
|---|---|---|
| T-01 Jezero | Both scales have `resolution_validated=false` and zero comparable terrain features. The measured regional record's `slope_p90_deg` sensitivity fails at 15.44% / 0.912°. | Reprocess the measured DEM at a supportable analysis scale; document independent resolution/uncertainty evidence. Keep failed p90 slope non-comparable unless a new measurement passes. Mark at least three other measured features comparable only after validation. |
| T-03 Marius Hills | Regional record has `resolution_validated=false` and zero comparable terrain features. `quality_review/marius_support.json` explicitly says the measured-bin diagnostic lacks an independent accuracy bound and approved acceptance policy. | Obtain or approve an independent accuracy bound and resolution acceptance rule, then rerun measured-only extraction at the accepted scale. Publish at least three passing comparable features. |

After new data is supplied, run `engine/.venv/bin/python -m engine.cli check --features
processing/out/real/features.json --features
processing/out/mars_measured/features.json --grid
processing/out/earth_grid.parquet`. Then rerun ranking and exports. A change to
the score formula cannot substitute for missing measurement validation.
