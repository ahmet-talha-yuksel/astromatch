# Validation report

ROC/AUC: skipped — Explicit negatives file required

Regional grid feature correlations: 216 cells (pairwise Spearman; see JSON matrix).

## Similarity-math acceptance

| Criterion | Result |
|---|---|
| loo_median50 | PASS |
| controls_reported | PASS |
| stability_spearman_ge_0_8 | PASS |

Old versus transformed-space decile histograms, control-site ranks, top-ten spans, and rank correlations are in validation_report.json.

- mars_jezero_local__local__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_local__local__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_local__local__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_local__local__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_regional__regional__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_regional__regional__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_regional__regional__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_jezero_regional__regional__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_local__local__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_local__local__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_local__local__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_local__local__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_regional__regional__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_regional__regional__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_regional__regional__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_shackleton_regional__regional__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_marius_hills_regional__regional__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_marius_hills_regional__regional__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_marius_hills_regional__regional__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- moon_marius_hills_regional__regional__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_phoenix_regional__regional__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_phoenix_regional__regional__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_phoenix_regional__regional__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_phoenix_regional__regional__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_arcadia_regional__regional__balanced: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_arcadia_regional__regional__landing_ops: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_arcadia_regional__regional__rover_mobility: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}
- mars_arcadia_regional__regional__geomorphology: 0 known analogs; recall 1/5/10%: {'1': None, '5': None, '10': None}

## Method sensitivity

- mars_jezero_regional__regional__balanced: Spearman=0.9970873371770232; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_jezero_regional__regional__landing_ops: Spearman=0.9967243220158019; top-10 Jaccard=1.0; method_sensitive=False
- mars_jezero_regional__regional__rover_mobility: Spearman=0.9972282724749091; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_jezero_regional__regional__geomorphology: Spearman=0.9969730941704034; top-10 Jaccard=0.5384615384615384; method_sensitive=False
- mars_phoenix_regional__regional__balanced: Spearman=0.9987945761264145; top-10 Jaccard=1.0; method_sensitive=False
- mars_phoenix_regional__regional__landing_ops: Spearman=0.9991180866965618; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_phoenix_regional__regional__rover_mobility: Spearman=0.9986365577621181; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_phoenix_regional__regional__geomorphology: Spearman=0.9989718129404228; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_arcadia_regional__regional__balanced: Spearman=0.9993252188767883; top-10 Jaccard=1.0; method_sensitive=False
- mars_arcadia_regional__regional__landing_ops: Spearman=0.99875400384369; top-10 Jaccard=0.6666666666666666; method_sensitive=False
- mars_arcadia_regional__regional__rover_mobility: Spearman=0.9993679265428146; top-10 Jaccard=1.0; method_sensitive=False
- mars_arcadia_regional__regional__geomorphology: Spearman=0.9995654494981849; top-10 Jaccard=1.0; method_sensitive=False
