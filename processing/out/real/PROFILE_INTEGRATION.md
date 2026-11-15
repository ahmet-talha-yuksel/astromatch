# Analog Profile integration status

The profile and context contract is consumed by the engine adapter merged in PR #42.
The original handoff's adapter errors (JSON-array `ctx__*__warnings`, profile-1.0
`targets`/`earth_sites`, nullable `verified_by`, lunar `surface_temp_*` keys, and
context precedence across measured feature files) have been resolved.

The 2025 MODIS context release merged from the parallel terrain/data work is
retained for Earth records and grid cells. The lunar Diviner context is retained
for three Moon target records. Earth precipitation remains null because IMERG
inputs were not supplied. Lunar temperatures and PSR fraction remain null:
the inspected PRP product cannot establish the requested measured surface
quantities or a validated permanent-shadow mask. These nulls carry explicit
reasons and must not be treated as similarity evidence.

`target_profiles.json` contains five targets and 16 Earth site/scale records.
Substantive claims have source links, but their `verified_by` fields remain null.
The API and UI display an **Unverified source** badge until human verification
is recorded. See `PROFILE_REVIEW.md` for the claim-by-claim review queue and
`context_report.md` for the measured Earth context coverage.

The topographic ranking features and eligibility flags are unchanged. Re-run
the engine pipeline after context or profiles are updated to refresh manifests
and precomputed results; profile characterization does not create a combined
terrain-plus-context score.
