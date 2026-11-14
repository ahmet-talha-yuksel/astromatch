# Explainable similarity engine

Python 3.11+; install `pip install -r engine/requirements.txt`. scikit-learn is installed by the requirements file; `hdbscan` remains optional for cluster agreement. From the repository root:

```bash
python -m engine.cli generate-mock --out engine/mock_data/
python -m engine.cli run --mock --preset all --timestamp 2026-01-01T00:00:00Z
python -m engine.cli validate --mock
python -m pytest validation/test_similarity.py engine/tests
```

The current processed fixtures are synthetic. Real mode rejects mock records. `--mock` uses generated mock records only and stamps outputs `MOCK DATA — NOT A SCIENTIFIC RESULT`.

For row-preserving validation scores, use `from engine.validation_api import score_grid` or `python -m engine.cli export-scores --mock --criteria --out engine/out/scores/`. The DataFrame interface returns 0–1 scores, `NaN` for ineligible cells, and optional per-criterion similarities. Its default sigma is recomputed from the input grid; `sigma="frozen"` holds reference sigma fixed for noise tests. See [VALIDATION_INTERFACE.md](VALIDATION_INTERFACE.md).

For each comparable feature, Gaussian similarity is `exp(-0.5*((x-t)/sigma)^2)`. Sigma is `max(floor, k*1.4826*MAD)` over same-scale Earth grid and reference records, excluding mock values in real mode; regional pooling or configured fallback applies when the sample count is low. Trapezoid and one-sided criteria are also supported. Only matching scales with validated resolution and explicitly comparable, non-null values participate. Configured weights renormalize over eligible features. The primary score is `100*exp(sum(w_i*log(max(s_i,.01))))`; arithmetic score (with the same 0.01 floor, ensuring geo ≤ arithmetic), criterion coverage, and a weak-link flag are also reported. Fewer than three eligible features excludes a candidate. Earth vegetation, humidity, and coast flags never affect the score unless filter mode explicitly excludes them. NMS separates local results by 20 km and regional results by 150 km.

Optional kNN, HDBSCAN, and PCA share the same features as the geometric score. Agreement therefore measures **methodological robustness, not independent confirmation**. These methods never change the primary score. Missing scikit-learn yields `agreement: unavailable`. Explanations are deterministic templates. Topography cannot establish mineralogy, radiation, habitability, landing safety, or atmosphere/gravity equivalence.

Environment overrides: `ASTROMATCH_FEATURES`, `ASTROMATCH_GRID`, `ASTROMATCH_KNOWN`. CLI paths override them. Outputs under `engine/out/` are ignored by Git. Pin `--timestamp` for byte-identical run outputs.

## Performance and local site cards

`python -m pytest -s engine/tests/test_perf.py` benchmarks the **full** public `rank(ds, target, 'regional', 'balanced', k=20)` path on 100,000 generated grid cells plus eight regional sites. It times eligibility, sigma, aggregation, novelty, NMS, output construction and optional ML. The test skips when `CI` is set. On the development machine with Python 3.14, one run took 0.848 s without ML and 2.562 s with scikit-learn ML; HDBSCAN was unavailable in that environment. Timings vary by hardware. The full score array is compact by default; top-k entries contain criterion details. `rank(..., detailed=True)` populates criterion details for every scored candidate and is used for validation and local-site exports.

Each local-scale CLI run writes `sites__{target}__local__{preset}.json` with all scored `earth_site` records, including Turkish and control sites. The site list is not cut to top-k and does not apply spatial NMS. It carries criterion details for frontend cards and lists any ineligible sites with reasons.

## Sparse-scale sigma and relative ranking

`min_sigma_samples` defaults to 200. A scale with fewer than 200 `earth_grid` and `earth_reference` values borrows their regional distribution; if no such values exist, it uses `fixed_fallback` from `config/features.yaml`. Every result and index entry records `value`, `sigma_source`, and `n_samples`. Fallback values are engineering defaults, not measurements.

`score_geo` remains the absolute primary score. `score_relative` sets the best eligible Earth candidate for each target/scale/preset to 100; `score_percentile` ranks it among scored Earth candidates. `match_level` reports absolute strong/moderate, relative-only (below 60 with relative score ≥90 locally, or top 5% regionally), or weak. Relative-only results explicitly say no close absolute Earth analog was found. Local site exports include `floored_criteria` and per-criterion similarity. `agreement_basis` states whether optional HDBSCAN clustering was available (`geo+knn+cluster`) or only geometric score and kNN (`geo+knn`).

## Real-data check and frozen demo

`python -m engine.cli check --features PATH [--grid PATH]` audits real records without ranking and exits 2 with actionable errors when they are not ready. A real-mode `run` performs the same check first. `python -m engine.cli export-demo --out engine/demo_results/` regenerates the committed, compact offline mock snapshot, validation report, and manifest. Pass `--timestamp` for byte-identical exports. The methodology is documented in [METHODOLOGY.md](METHODOLOGY.md).
