# v6 versus v9 real-data comparison

Inputs: `main@cbb06c4` (`processing/out/real/features.json`, `processing/out/mars_measured/features.json`, `processing/out/earth_grid.parquet`). Same inputs and presets for both feature sets. Regional rankings below use the full eligible ordering before spatial NMS. Scores are raw topographic scores, not probabilities.

## Acceptance criteria

| Criterion | v6 | v9 |
|---|---|---|
| loo_median50 | PASS | PASS |
| stability_spearman_ge_0_8 | PASS | PASS |
| controls_reported | PASS | PASS |

Regional calibrated k: v6 `1.107180`; v9 `1.222905`. Both achieved median pairwise score 50 within ±2.

## mars_arcadia_regional · regional

- v6: 6 features; top-10 span 0.71; top-tier size 11; ≥90 share 0.35; ≥80 share 0.50.
- v9: 6 features; top-10 span 0.58; top-tier size 10; ≥90 share 0.38; ≥80 share 0.55.
- v6/v9 Spearman: 1.00; top-10 overlap: 10/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Halitpasa, Manisa, TR | 99.9 [99.4–99.9] | 99.54 | Halitpasa, Manisa, TR | 99.9 [99.6–99.9] | 99.54 |
| 2 | Beysehir, Konya, TR | 99.7 [99.1–99.8] | 99.07 | Beysehir, Konya, TR | 99.7 [99.3–99.9] | 99.07 |
| 3 | Cobanlar, Afyonkarahisar, TR | 99.6 [99.1–99.8] | 98.61 | Cobanlar, Afyonkarahisar, TR | 99.7 [99.2–99.8] | 98.61 |
| 4 | Antofagasta, Antofagasta, CL | 99.5 [98.9–99.8] | 98.61 | Antofagasta, Antofagasta, CL | 99.6 [99.1–99.8] | 98.61 |
| 5 | Gelegra, Ankara, TR | 99.4 [98.7–99.6] | 98.15 | Gelegra, Ankara, TR | 99.5 [99.0–99.7] | 98.15 |
| 6 | Savcili, Kirsehir, TR | 99.4 [98.8–99.6] | 97.69 | Savcili, Kirsehir, TR | 99.5 [99.0–99.7] | 97.69 |
| 7 | Yunak, Konya, TR | 99.4 [98.6–99.7] | 97.22 | Yunak, Konya, TR | 99.5 [98.7–99.7] | 97.22 |
| 8 | Guellue, Usak, TR | 99.3 [98.7–99.6] | 96.76 | Guellue, Usak, TR | 99.4 [98.8–99.7] | 96.76 |
| 9 | Vestmannaeyjar, South, IS | 99.3 [98.6–99.6] | 96.30 | Vestmannaeyjar, South, IS | 99.4 [98.8–99.6] | 96.30 |
| 10 | Urla, Izmir, TR | 99.2 [98.1–99.5] | 95.83 | Urla, Izmir, TR | 99.3 [98.6–99.6] | 95.83 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 4 | 4 |
| haughton | 59 | 59 |
| meteor_crater | 101 | 101 |

## mars_jezero_local · local

Unscorable: resolution_not_validated. No ranking claimed.

## mars_jezero_regional · regional

- v6: 5 features; top-10 span 1.61; top-tier size 5; ≥90 share 0.38; ≥80 share 0.53.
- v9: 5 features; top-10 span 1.33; top-tier size 6; ≥90 share 0.43; ≥80 share 0.54.
- v6/v9 Spearman: 1.00; top-10 overlap: 10/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Misli, Nigde, TR | 99.9 [99.5–99.9] | 99.54 | Misli, Nigde, TR | 99.9 [99.6–99.9] | 99.54 |
| 2 | Saudarkrokur, Northwest, IS | 99.5 [98.9–99.7] | 99.07 | Saudarkrokur, Northwest, IS | 99.6 [99.2–99.8] | 99.07 |
| 3 | Civril, Denizli, TR | 99.4 [98.7–99.6] | 98.61 | Civril, Denizli, TR | 99.5 [99.0–99.7] | 98.61 |
| 4 | Pyrgos, Limassol, CY | 99.2 [98.6–99.6] | 98.15 | Pyrgos, Limassol, CY | 99.4 [98.7–99.6] | 98.15 |
| 5 | Argithani, Konya, TR | 99.2 [98.4–99.5] | 97.69 | Argithani, Konya, TR | 99.3 [98.8–99.6] | 97.69 |
| 6 | Antofagasta, Antofagasta, CL | 99.1 [98.4–99.5] | 97.22 | Antofagasta, Antofagasta, CL | 99.3 [98.6–99.6] | 97.22 |
| 7 | Kadinhani, Konya, TR | 99.0 [98.2–99.3] | 96.76 | Kadinhani, Konya, TR | 99.2 [98.5–99.5] | 96.76 |
| 8 | Bolvadin, Afyonkarahisar, TR | 98.8 [97.9–99.3] | 96.30 | Bolvadin, Afyonkarahisar, TR | 99.0 [98.4–99.4] | 96.30 |
| 9 | Saudarkrokur, Northwest, IS | 98.7 [97.7–99.2] | 95.83 | Saudarkrokur, Northwest, IS | 98.9 [98.2–99.3] | 95.83 |
| 10 | Beylikova, Eskisehir, TR | 98.2 [97.3–98.8] | 95.37 | Beylikova, Eskisehir, TR | 98.6 [97.7–99.0] | 95.37 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 18 | 18 |
| haughton | 113 | 113 |
| meteor_crater | 102 | 102 |

## mars_phoenix_regional · regional

- v6: 6 features; top-10 span 2.24; top-tier size 18; ≥90 share 0.15; ≥80 share 0.27.
- v9: 6 features; top-10 span 1.84; top-tier size 18; ≥90 share 0.17; ≥80 share 0.33.
- v6/v9 Spearman: 1.00; top-10 overlap: 10/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Umraniye, Afyonkarahisar, TR | 99.5 [97.4–99.7] | 99.54 | Umraniye, Afyonkarahisar, TR | 99.6 [97.7–99.7] | 99.54 |
| 2 | Suluklu, Konya, TR | 99.2 [97.0–99.5] | 99.07 | Suluklu, Konya, TR | 99.4 [97.2–99.6] | 99.07 |
| 3 | Yeniceoba, Konya, TR | 99.0 [96.6–99.5] | 98.61 | Yeniceoba, Konya, TR | 99.2 [96.7–99.6] | 98.61 |
| 4 | Mitzpe Ramon, Southern District, IL | 98.9 [96.3–99.4] | 98.15 | Mitzpe Ramon, Southern District, IL | 99.1 [97.0–99.5] | 98.15 |
| 5 | Arish, Muhafazat Shamal Sina', EG | 98.8 [96.0–99.5] | 97.69 | Arish, Muhafazat Shamal Sina', EG | 99.0 [96.8–99.5] | 97.69 |
| 6 | Ismailia, Al Isma'iliyah, EG | 98.4 [94.7–99.1] | 97.22 | Ismailia, Al Isma'iliyah, EG | 98.7 [95.4–99.3] | 97.22 |
| 7 | Hotamis, Konya, TR | 98.2 [93.3–98.9] | 96.76 | Hotamis, Konya, TR | 98.5 [95.3–99.2] | 96.76 |
| 8 | Al `Alamayn, Muhafazat Matruh, EG | 97.6 [93.0–98.7] | 96.30 | Al `Alamayn, Muhafazat Matruh, EG | 98.1 [94.4–98.8] | 96.30 |
| 9 | Arish, Muhafazat Shamal Sina', EG | 97.5 [93.3–98.6] | 95.83 | Arish, Muhafazat Shamal Sina', EG | 98.0 [94.1–98.9] | 95.83 |
| 10 | Bilbays, Eastern Province, EG | 97.3 [90.9–98.8] | 94.91 | Bilbays, Eastern Province, EG | 97.7 [92.7–98.8] | 94.91 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 81 | 81 |
| haughton | 33 | 33 |
| meteor_crater | 39 | 39 |

## moon_marius_hills_regional · regional

Unscorable: resolution_not_validated. No ranking claimed.

## moon_shackleton_local · local

- v6: 6 features; top-10 span 7.29; top-tier size 4; ≥90 share —; ≥80 share —.
- v9: 9 features; top-10 span 25.81; top-tier size 4; ≥90 share —; ≥80 share —.
- v6/v9 Spearman: 0.93; top-10 overlap: 8/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Antofagasta, Antofagasta, CL | 8.3 [4.7–12.4] | — | Antofagasta, Antofagasta, CL | 27.4 [19.1–34.1] | — |
| 2 | Yesilova, Burdur, TR | 7.1 [3.8–11.0] | — | Menye, Manisa, TR | 18.5 [11.7–23.4] | — |
| 3 | Menye, Manisa, TR | 4.1 [2.5–6.7] | — | Asagi Karafakili, Hatay, TR | 18.2 [12.4–26.4] | — |
| 4 | Asagi Karafakili, Hatay, TR | 6.5 [4.2–9.7] | — | Yesilova, Burdur, TR | 17.9 [11.4–24.1] | — |
| 5 | Karapinar, Konya, TR | 2.0 [1.4–3.0] | — | Karapinar, Konya, TR | 10.6 [6.2–14.9] | — |
| 6 | Gjoa Haven, Nunavut, CA | 1.3 [1.1–1.8] | — | Gjoa Haven, Nunavut, CA | 5.5 [3.4–8.0] | — |
| 7 | LeChee, Arizona, US | 1.0 [1.0–1.0] | — | LeChee, Arizona, US | 1.6 [1.3–2.6] | — |
| 8 | Sereflikochisar, Ankara, TR | 1.0 [1.0–1.0] | — | Sereflikochisar, Ankara, TR | 1.8 [1.3–2.6] | — |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 1 | 1 |
| haughton | 6 | 6 |
| meteor_crater | 7 | 7 |

## moon_shackleton_regional · regional

- v6: 6 features; top-10 span 10.55; top-tier size 1; ≥90 share 0.04; ≥80 share 0.09.
- v9: 9 features; top-10 span 7.04; top-tier size 8; ≥90 share 0.02; ≥80 share 0.09.
- v6/v9 Spearman: 0.99; top-10 overlap: 8/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Camliyayla, Mersin, TR | 98.8 [98.3–99.1] | 99.54 | Halkapinar, Konya, TR | 93.0 [90.9–94.0] | 99.54 |
| 2 | Anamur, Mersin, TR | 95.5 [94.1–96.2] | 99.07 | Altinyaka, Antalya, TR | 92.6 [89.1–94.7] | 99.07 |
| 3 | Altinyaka, Antalya, TR | 95.3 [93.3–96.6] | 98.61 | Anamur, Mersin, TR | 92.0 [88.3–94.1] | 98.61 |
| 4 | Koprulu, Antalya, TR | 95.0 [92.9–96.3] | 98.15 | Mut, Mersin, TR | 91.4 [88.7–92.9] | 98.15 |
| 5 | Uzumlu, Mugla, TR | 94.0 [91.9–95.2] | 97.69 | Camliyayla, Mersin, TR | 89.8 [83.8–94.0] | 97.69 |
| 6 | Beskonak, Antalya, TR | 92.7 [89.7–94.4] | 97.22 | Beskonak, Antalya, TR | 89.3 [84.0–92.2] | 97.22 |
| 7 | Halkapinar, Konya, TR | 90.9 [88.2–92.4] | 96.76 | Elvanli, Mersin, TR | 87.8 [84.0–90.2] | 96.76 |
| 8 | Mut, Mersin, TR | 90.3 [87.2–91.9] | 96.30 | Koprulu, Antalya, TR | 87.3 [77.6–93.2] | 96.30 |
| 9 | Okurcalar, Antalya, TR | 89.1 [86.4–90.7] | 95.83 | Uzumlu, Mugla, TR | 86.8 [80.2–91.0] | 95.83 |
| 10 | Kas, Antalya, TR | 88.3 [85.1–89.8] | 95.37 | Taltal, Antofagasta, CL | 85.9 [82.5–88.3] | 95.37 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 85 | 85 |
| haughton | 120 | 116 |
| meteor_crater | 128 | 122 |

## Nine-feature grid correlations

Pairwise Spearman over validated regional grid cells (`n=216`); columns and rows use the active v9 features.

| Feature | slope_median_deg | slope_p90_deg | flat_fraction | tri_median_m | relief_m | elevation_std_m | hypsometric_integral | roughness_ratio | curvature_std_per_km |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| slope_median_deg | 1.00 | 0.78 | -0.76 | 1.00 | 0.81 | 0.78 | 0.51 | 0.56 | 0.75 |
| slope_p90_deg | 0.78 | 1.00 | -0.97 | 0.79 | 0.95 | 0.95 | 0.13 | 0.23 | 0.98 |
| flat_fraction | -0.76 | -0.97 | 1.00 | -0.77 | -0.91 | -0.93 | -0.07 | -0.20 | -0.98 |
| tri_median_m | 1.00 | 0.79 | -0.77 | 1.00 | 0.82 | 0.79 | 0.49 | 0.56 | 0.76 |
| relief_m | 0.81 | 0.95 | -0.91 | 0.82 | 1.00 | 0.99 | 0.22 | 0.22 | 0.91 |
| elevation_std_m | 0.78 | 0.95 | -0.93 | 0.79 | 0.99 | 1.00 | 0.17 | 0.17 | 0.93 |
| hypsometric_integral | 0.51 | 0.13 | -0.07 | 0.49 | 0.22 | 0.17 | 1.00 | 0.64 | 0.10 |
| roughness_ratio | 0.56 | 0.23 | -0.20 | 0.56 | 0.22 | 0.17 | 0.64 | 1.00 | 0.21 |
| curvature_std_per_km | 0.75 | 0.98 | -0.98 | 0.76 | 0.91 | 0.93 | 0.10 | 0.21 | 1.00 |

## Possible flattened surfaces

Validated Earth records with `roughness_ratio = 0` (nearest populated place is a locator, not a land classification):

| Record | Kind | Lat | Lon | Nearest place |
|---|---|---:|---:|---|
| earth_grid_r251_c412 | earth_grid | 35.75 | 26.25 | Palekastro, Crete, GR |
| earth_grid_r251_c413 | earth_grid | 35.75 | 26.75 | Fry, South Aegean, GR |
| earth_grid_r251_c414 | earth_grid | 35.75 | 27.25 | Karpathos, South Aegean, GR |
| earth_grid_r252_c412 | earth_grid | 36.25 | 26.25 | Astypalaia, South Aegean, GR |
| earth_grid_r252_c413 | earth_grid | 36.25 | 26.75 | Astypalaia, South Aegean, GR |
| earth_grid_r253_c412 | earth_grid | 36.75 | 26.25 | Astypalaia, South Aegean, GR |
| earth_grid_r253_c413 | earth_grid | 36.75 | 26.75 | Kefalos, South Aegean, GR |
| earth_grid_r254_c410 | earth_grid | 37.25 | 25.25 | Naousa, South Aegean, GR |
| earth_grid_r254_c411 | earth_grid | 37.25 | 25.75 | Filotion, South Aegean, GR |
| earth_grid_r254_c412 | earth_grid | 37.25 | 26.25 | Skala, South Aegean, GR |
| earth_grid_r254_c413 | earth_grid | 37.25 | 26.75 | Leipsoi, South Aegean, GR |
| earth_grid_r257_c412 | earth_grid | 38.75 | 26.25 | Oinousses, North Aegean, GR |

12 validated grid cells; no validated Earth sites have zero roughness ratio.

## Eligibility and default

v9 is the default because all three pre-registered acceptance criteria pass. Shackleton local/regional uses nine features. Phoenix and Arcadia use six; Jezero regional uses five because `slope_p90_deg` fails delivered sensitivity and all three shape verdicts are absent. Marius and Jezero local remain unscorable. Mars shape features will become eligible only after per-feature sensitivity verdicts are delivered.
