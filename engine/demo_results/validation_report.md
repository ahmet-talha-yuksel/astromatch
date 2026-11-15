# Validation report

ROC/AUC: skipped — Explicit negatives file required

Regional grid feature correlations: 216 cells (pairwise Spearman; see JSON matrix).

## Similarity-math acceptance

| Criterion | Result |
|---|---|
| loo_median50 | PASS |
| controls_reported | PASS |
| stability_spearman_ge_0_8 | PASS |

## Plausibility: mars_jezero_regional__regional

| Feature | Target raw | Top 1 raw (sᵢ) | Top 2 raw (sᵢ) | Top 3 raw (sᵢ) |
|---|---:|---:|---:|---:|
| slope_median_deg | 1.441 | 1.775 (0.995) | 1.377 (1.000) | 1.796 (0.994) |
| flat_fraction | 0.8421 | 0.8688 (0.997) | 0.9248 (0.959) | 0.868 (0.997) |
| tri_median_m | 75.36 | 94.05 (0.994) | 63.1 (0.996) | 96.86 (0.992) |
| relief_m | 805.8 | 781.9 (1.000) | 798.1 (1.000) | 1016 (0.981) |
| elevation_std_m | 275.6 | 237.1 (0.991) | 243.6 (0.994) | 310.5 (0.994) |
| hypsometric_integral | 0.3959 | 0.3508 (0.975) | 0.3207 (0.932) | 0.3045 (0.901) |
| roughness_ratio | 0.1887 | 0.2258 (0.856) | 0.2221 (0.880) | 0.216 (0.916) |

## Plausibility: moon_shackleton_local__local

| Feature | Target raw | Top 1 raw (sᵢ) | Top 2 raw (sᵢ) | Top 3 raw (sᵢ) |
|---|---:|---:|---:|---:|
| slope_median_deg | 23.48 | 2.796 (0.109) | 2.597 (0.093) | 0.9323 (0.007) |
| slope_p90_deg | 31.23 | 8.809 (0.352) | 5.703 (0.153) | 8.368 (0.323) |
| flat_fraction | 0.1425 | 0.69 (0.428) | 0.83 (0.236) | 0.7825 (0.303) |
| tri_median_m | 457.4 | 89.49 (0.333) | 70.69 (0.237) | 18.53 (0.015) |
| relief_m | 1569 | 264.1 (0.111) | 227.3 (0.075) | 353.1 (0.213) |
| elevation_std_m | 525.5 | 91.9 (0.224) | 66.43 (0.123) | 123.9 (0.358) |
| hypsometric_integral | 0.2722 | 0.1712 (0.728) | 0.392 (0.640) | 0.1314 (0.540) |
| roughness_ratio | 0.1822 | 0.3805 (0.552) | 0.368 (0.582) | 0.124 (0.857) |
| curvature_std_per_km | 0.2132 | 0.2011 (0.987) | 0.1478 (0.591) | 0.1637 (0.760) |

## Plausibility: moon_shackleton_regional__regional

| Feature | Target raw | Top 1 raw (sᵢ) | Top 2 raw (sᵢ) | Top 3 raw (sᵢ) |
|---|---:|---:|---:|---:|
| slope_median_deg | 8.393 | 5.072 (0.968) | 7.782 (0.999) | 4.823 (0.961) |
| slope_p90_deg | 22.77 | 13.09 (0.900) | 16.41 (0.964) | 14.51 (0.932) |
| flat_fraction | 0.2596 | 0.4908 (0.940) | 0.2948 (0.998) | 0.5132 (0.930) |
| tri_median_m | 413.4 | 272 (0.978) | 395.6 (1.000) | 302.2 (0.988) |
| relief_m | 2783 | 1697 (0.916) | 1905 (0.950) | 2068 (0.969) |
| elevation_std_m | 918.3 | 515.4 (0.870) | 553.4 (0.898) | 698.5 (0.969) |
| hypsometric_integral | 0.5842 | 0.5361 (0.971) | 0.4807 (0.875) | 0.4454 (0.786) |
| roughness_ratio | 0.2404 | 0.2851 (0.867) | 0.3212 (0.660) | 0.3209 (0.662) |
| curvature_std_per_km | 0.1367 | 0.139 (1.000) | 0.1706 (0.981) | 0.1552 (0.994) |

## Plausibility: mars_phoenix_regional__regional

| Feature | Target raw | Top 1 raw (sᵢ) | Top 2 raw (sᵢ) | Top 3 raw (sᵢ) |
|---|---:|---:|---:|---:|
| slope_median_deg | 0.5178 | 0.277 (0.961) | 0.5684 (0.999) | 0.9067 (0.965) |
| slope_p90_deg | 1.819 | 1.578 (0.993) | 1.162 (0.937) | 2.246 (0.985) |
| flat_fraction | 0.9794 | 0.9864 (0.989) | 1 (0.968) | 0.9972 (0.968) |
| tri_median_m | 26.66 | 17.39 (0.978) | 28.91 (0.999) | 49.47 (0.954) |
| relief_m | 243.4 | 319.3 (0.974) | 174.6 (0.962) | 209.5 (0.992) |
| elevation_std_m | 88.38 | 131.1 (0.938) | 57.69 (0.928) | 68.03 (0.972) |
| hypsometric_integral | 0.6677 | 0.4746 (0.627) | 0.5145 (0.745) | 0.3746 (0.341) |
| roughness_ratio | 0.2749 | 0.217 (0.761) | 0.3038 (0.952) | 0.3329 (0.833) |
| curvature_std_per_km | 0.03079 | 0.021 (0.947) | 0.01074 (0.671) | 0.02434 (0.980) |

## Plausibility: mars_arcadia_regional__regional

| Feature | Target raw | Top 1 raw (sᵢ) | Top 2 raw (sᵢ) | Top 3 raw (sᵢ) |
|---|---:|---:|---:|---:|
| slope_median_deg | 1.561 | 1.251 (0.994) | 1.447 (0.999) | 1.073 (0.983) |
| slope_p90_deg | 5.563 | 5.199 (0.998) | 5.877 (0.999) | 4.438 (0.983) |
| flat_fraction | 0.8828 | 0.8928 (0.999) | 0.848 (0.995) | 0.916 (0.992) |
| tri_median_m | 72.74 | 64.69 (0.998) | 75.7 (1.000) | 53.51 (0.988) |
| relief_m | 555.9 | 511.6 (0.998) | 583 (0.999) | 465.1 (0.989) |
| elevation_std_m | 194.4 | 178.6 (0.997) | 196.1 (1.000) | 169.5 (0.992) |
| hypsometric_integral | 0.1714 | 0.1665 (1.000) | 0.139 (0.987) | 0.1361 (0.985) |
| roughness_ratio | 0.2116 | 0.2274 (0.975) | 0.2286 (0.972) | 0.1938 (0.964) |

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

- mars_jezero_regional__regional__balanced: Spearman=0.9933205210335252; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_jezero_regional__regional__landing_ops: Spearman=0.9940679051889811; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_jezero_regional__regional__rover_mobility: Spearman=0.9953747597693785; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_jezero_regional__regional__geomorphology: Spearman=0.9963527653213751; top-10 Jaccard=0.6666666666666666; method_sensitive=False
- mars_phoenix_regional__regional__balanced: Spearman=0.998731582319026; top-10 Jaccard=0.5384615384615384; method_sensitive=False
- mars_phoenix_regional__regional__landing_ops: Spearman=0.9991554559043347; top-10 Jaccard=1.0; method_sensitive=False
- mars_phoenix_regional__regional__rover_mobility: Spearman=0.9990486867392694; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_phoenix_regional__regional__geomorphology: Spearman=0.9989579329489644; top-10 Jaccard=1.0; method_sensitive=False
- mars_arcadia_regional__regional__balanced: Spearman=0.9985511424300663; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_arcadia_regional__regional__landing_ops: Spearman=0.9984347640401451; top-10 Jaccard=1.0; method_sensitive=False
- mars_arcadia_regional__regional__rover_mobility: Spearman=0.9990978005551997; top-10 Jaccard=0.8181818181818182; method_sensitive=False
- mars_arcadia_regional__regional__geomorphology: Spearman=0.9990486867392694; top-10 Jaccard=1.0; method_sensitive=False
