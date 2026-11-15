# Analog-profile handoff: integration blockers

Branch base: 865a534 (main). The task contract is preserved; engine files were not changed.

1. `engine/adapters.py:extract_context` only recognizes value/source/period/evidence/data_status suffixes. `ctx__<name>__warnings` is a JSON array string as requested; the adapter parses it as a list and applies scalar `pd.isna`, raising `ValueError: The truth value of an empty array is ambiguous`. The real grid load consequently drops all 408 rows. Correct consumer behavior must preserve warnings and month counts as metadata rather than replacing the quantity value.
2. `engine/analog_profile.py:read_profiles` expects a `records` list with kind and data_status. The requested profile-1.0 file uses targets/earth_sites lists. It also rejects `verified_by=null`, although human verification must remain null in this task. Unknown/not_applicable source-null dimensions are currently rejected as unsourced claims. These require a consumer contract decision; no invented verification or citations were added to appease it.
3. `engine/analog_profile.py:CONTEXT_KEYS` uses diviner_day_max_c/diviner_night_min_c/diviner_mean_c rather than the requested surface_temp_max_c/surface_temp_min_c/surface_temp_mean_c. Requested lunar context keys are kept, with nulls and reasons.
4. The engine loads measured Mars/Moon records after real/features.json, so lunar real-record context can be superseded by moon_measured records. No other feature file was modified to mask this precedence.

CI on the A/B commits failed (example run: https://github.com/ahmet-talha-yuksel/astromatch/actions/runs/43704784125). This is not a merge-ready delivery. A/B observation acquisition is blocked and the source-specific profile coverage is partial.

## Local verification

- New context/lunar/profile tests: 12 passed.
- Full processing suite after excluding ctx__ columns only from historical grid/schema comparisons: 156 passed, 1 skipped, 5 failed.
- Separate unmodified 865a534 processing archive: 143 passed, 1 skipped, 6 failed. The remaining five failing tests are also in that baseline: test_target_reviews_bind_current_release_without_promoting_rejected_targets; test_reproducible_and_checked_in; test_offline_backfill_is_idempotent_and_preserves_legacy_data; test_handoff_contains_separate_measured_exports_and_current_controls; test_real_reviewed_package_unlocks_only_qualified_pairs.
- Snapshot tests now compare non-context feature attributes and original Arrow columns; new preservation tests independently bind all original values/IDs to semantic SHA256 digests. No scoring value, eligibility flag, ID or original Arrow type was changed.

## Reproduction

Use Python 3.12 and `pip install -r processing/requirements.txt`.

```
python -m processing.scripts.analog_context
python -m processing.scripts.lunar_context
python -m processing.scripts.target_profiles
python -m pytest processing/tests/test_analog_context.py processing/tests/test_lunar_context.py processing/tests/test_target_profiles.py -q
```

The first builder explicitly emits unavailable-observation records; it is not a downloader and does not extract a 2025 climate series. Earthaccess 0.19.0 was installed and both noninteractive login strategies were attempted; no credentials were available. Credential provisioning, authenticated monthly extraction with exact window/QA support and validated Diviner surface-window sampling are still needed. The annual aggregation helpers alone do not complete those missing stages.
