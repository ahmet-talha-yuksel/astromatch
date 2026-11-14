# Explainable similarity engine

Python 3.11+; install `pip install -r engine/requirements.txt`. Optional: `pip install 'scikit-learn>=1.3' hdbscan` for confidence methods. From the repository root:

```bash
python -m engine.cli generate-mock --out engine/mock_data/
python -m engine.cli run --mock --preset all --timestamp 2026-01-01T00:00:00Z
python -m engine.cli validate --mock
python -m pytest validation/test_similarity.py engine/tests
```

The current processed fixtures are synthetic. Real mode rejects mock records. `--mock` uses generated mock records only and stamps outputs `MOCK DATA — NOT A SCIENTIFIC RESULT`.

For each comparable feature, Gaussian similarity is `exp(-0.5*((x-t)/sigma)^2)`. Sigma is `max(floor, k*1.4826*MAD)` over Earth records of the same scale, excluding mock values in real mode. Trapezoid and one-sided criteria are also supported. Only matching scales with validated resolution and explicitly comparable, non-null values participate. Configured weights renormalize over eligible features. The primary score is `100*exp(sum(w_i*log(max(s_i,.01))))`; arithmetic score (with the same 0.01 floor, ensuring geo ≤ arithmetic), criterion coverage, and a weak-link flag are also reported. Fewer than three eligible features excludes a candidate. Earth vegetation, humidity, and coast flags never affect the score unless filter mode explicitly excludes them. NMS separates local results by 20 km and regional results by 150 km.

Optional kNN, HDBSCAN, and PCA share the same features as the geometric score. Agreement therefore measures **methodological robustness, not independent confirmation**. These methods never change the primary score. Missing scikit-learn yields `agreement: unavailable`. Explanations are deterministic templates. Topography cannot establish mineralogy, radiation, habitability, landing safety, or atmosphere/gravity equivalence.

Environment overrides: `ASTROMATCH_FEATURES`, `ASTROMATCH_GRID`, `ASTROMATCH_KNOWN`. CLI paths override them. Outputs under `engine/out/` are ignored by Git. Pin `--timestamp` for byte-identical run outputs.

## Performance and local site cards

`python -m pytest -s engine/tests/test_perf.py` benchmarks the **full** public `rank(ds, target, 'regional', 'balanced', k=20)` path on 100,000 generated grid cells plus eight regional sites. It times eligibility, sigma, aggregation, novelty, NMS, output construction and optional ML. The test skips when `CI` is set. On the development machine with Python 3.14, one run took 0.950 s without ML and 2.668 s with scikit-learn ML; HDBSCAN was unavailable in that environment. Timings vary by hardware. The full score array is compact by default; top-k entries contain criterion details. `rank(..., detailed=True)` populates criterion details for every scored candidate and is used for validation and local-site exports.

Each local-scale CLI run writes `sites__{target}__local__{preset}.json` with all scored `earth_site` records, including Turkish and control sites. The site list is not cut to top-k and does not apply spatial NMS. It carries criterion details for frontend cards and lists any ineligible sites with reasons.
