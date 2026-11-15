# v6 versus v9 real-data comparison

Inputs: `feature/terrain3d-improvements@217870c` (`processing/out/real/features.json`, `processing/out/mars_measured/features.json`, `processing/out/moon_measured/features.json`, `processing/out/earth_grid.parquet`). Same inputs and presets for both feature sets. Regional rankings below use the full eligible ordering before spatial NMS. Scores are raw topographic scores, not probabilities.

## Acceptance criteria

| Criterion | v6 | v9 |
|---|---|---|
| loo_median50 | PASS | PASS |
| stability_spearman_ge_0_8 | PASS | PASS |
| controls_reported | PASS | PASS |

Regional calibrated k: v6 `1.107180`; v9 `1.222905`. Both achieved median pairwise score 50 within ±2.

## mars_arcadia_regional · regional

- v6: 6 features; top-10 span 0.71; top-tier size 11; ≥90 share 0.35; ≥80 share 0.50.
- v9: 8 features; top-10 span 2.84; top-tier size 5; ≥90 share 0.22; ≥80 share 0.45.
- v6/v9 Spearman: 0.92; top-10 overlap: 4/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Halitpasa, Manisa, TR | 99.9 [99.4–99.9] | 99.54 | Beysehir, Konya, TR | 99.6 [99.0–99.8] | 99.54 |
| 2 | Beysehir, Konya, TR | 99.7 [99.1–99.8] | 99.07 | Halitpasa, Manisa, TR | 99.5 [98.8–99.8] | 99.07 |
| 3 | Cobanlar, Afyonkarahisar, TR | 99.6 [99.1–99.8] | 98.61 | Karaman, Karaman, TR | 98.6 [97.7–99.0] | 98.61 |
| 4 | Antofagasta, Antofagasta, CL | 99.5 [98.9–99.8] | 98.61 | Agia Paraskevi, North Aegean, GR | 98.5 [97.3–99.1] | 98.15 |
| 5 | Gelegra, Ankara, TR | 99.4 [98.7–99.6] | 98.15 | Cobanlar, Afyonkarahisar, TR | 98.2 [96.5–99.2] | 97.69 |
| 6 | Savcili, Kirsehir, TR | 99.4 [98.8–99.6] | 97.69 | Civril, Denizli, TR | 98.0 [96.6–98.8] | 97.22 |
| 7 | Yunak, Konya, TR | 99.4 [98.6–99.7] | 97.22 | Antofagasta, Antofagasta, CL | 97.9 [96.4–98.9] | 97.22 |
| 8 | Guellue, Usak, TR | 99.3 [98.7–99.6] | 96.76 | Misli, Nigde, TR | 97.8 [96.4–98.5] | 96.76 |
| 9 | Vestmannaeyjar, South, IS | 99.3 [98.6–99.6] | 96.30 | Dalaman, Mugla, TR | 96.7 [94.9–97.9] | 95.83 |
| 10 | Urla, Izmir, TR | 99.2 [98.1–99.5] | 95.83 | Mammari, Lefkosia, CY | 96.8 [95.0–97.4] | 96.30 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 4 | 7 |
| haughton | 59 | 143 |
| meteor_crater | 101 | 67 |

## mars_jezero_local · local

Unscorable: resolution_not_validated. No ranking claimed.

## mars_jezero_regional · regional

- v6: 5 features; top-10 span 1.61; top-tier size 5; ≥90 share 0.38; ≥80 share 0.53.
- v9: 7 features; top-10 span 5.85; top-tier size 8; ≥90 share 0.08; ≥80 share 0.44.
- v6/v9 Spearman: 0.93; top-10 overlap: 5/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Misli, Nigde, TR | 99.9 [99.5–99.9] | 99.54 | Saudarkrokur, Northwest, IS | 97.9 [95.9–99.0] | 99.54 |
| 2 | Saudarkrokur, Northwest, IS | 99.5 [98.9–99.7] | 99.07 | Antofagasta, Antofagasta, CL | 97.5 [95.7–98.5] | 99.07 |
| 3 | Civril, Denizli, TR | 99.4 [98.7–99.6] | 98.61 | Saudarkrokur, Northwest, IS | 97.2 [95.5–98.2] | 98.61 |
| 4 | Pyrgos, Limassol, CY | 99.2 [98.6–99.6] | 98.15 | Taltal, Antofagasta, CL | 96.4 [93.6–98.0] | 98.15 |
| 5 | Argithani, Konya, TR | 99.2 [98.4–99.5] | 97.69 | Antofagasta, Antofagasta, CL | 94.5 [91.3–96.3] | 98.15 |
| 6 | Antofagasta, Antofagasta, CL | 99.1 [98.4–99.5] | 97.22 | Inonu, Karaman, TR | 93.4 [88.3–96.7] | 97.69 |
| 7 | Kadinhani, Konya, TR | 99.0 [98.2–99.3] | 96.76 | Akdere, Mersin, TR | 93.0 [88.2–95.5] | 97.22 |
| 8 | Bolvadin, Afyonkarahisar, TR | 98.8 [97.9–99.3] | 96.30 | Salmanli, Yozgat, TR | 92.1 [85.5–96.2] | 96.30 |
| 9 | Saudarkrokur, Northwest, IS | 98.7 [97.7–99.2] | 95.83 | Misli, Nigde, TR | 92.3 [85.3–96.2] | 96.76 |
| 10 | Beylikova, Eskisehir, TR | 98.2 [97.3–98.8] | 95.37 | Kadinhani, Konya, TR | 92.0 [86.7–95.7] | 95.83 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 18 | 5 |
| haughton | 113 | 144 |
| meteor_crater | 102 | 30 |

## mars_phoenix_regional · regional

- v6: 6 features; top-10 span 2.24; top-tier size 18; ≥90 share 0.15; ≥80 share 0.27.
- v9: 9 features; top-10 span 6.56; top-tier size 32; ≥90 share 0.01; ≥80 share 0.12.
- v6/v9 Spearman: 0.86; top-10 overlap: 3/10.

| Rank | v6 place | v6 score [p5–p95] | v6 percentile | v9 place | v9 score [p5–p95] | v9 percentile |
|---:|---|---:|---:|---|---:|---:|
| 1 | Umraniye, Afyonkarahisar, TR | 99.5 [97.4–99.7] | 99.54 | Mersa Matruh, Muhafazat Matruh, EG | 91.5 [85.9–94.1] | 99.54 |
| 2 | Suluklu, Konya, TR | 99.2 [97.0–99.5] | 99.07 | Beheira, Al Buhayrah, EG | 91.5 [83.9–93.8] | 99.07 |
| 3 | Yeniceoba, Konya, TR | 99.0 [96.6–99.5] | 98.61 | Karahasanli, Nevsehir, TR | 88.3 [78.9–92.8] | 98.61 |
| 4 | Mitzpe Ramon, Southern District, IL | 98.9 [96.3–99.4] | 98.15 | Kulu, Konya, TR | 88.0 [79.9–92.7] | 98.15 |
| 5 | Arish, Muhafazat Shamal Sina', EG | 98.8 [96.0–99.5] | 97.69 | Yeniceoba, Konya, TR | 86.6 [74.4–93.3] | 97.69 |
| 6 | Ismailia, Al Isma'iliyah, EG | 98.4 [94.7–99.1] | 97.22 | Mitzpe Ramon, Southern District, IL | 86.4 [77.2–91.5] | 97.22 |
| 7 | Hotamis, Konya, TR | 98.2 [93.3–98.9] | 96.76 | Al `Alamayn, Muhafazat Matruh, EG | 86.3 [74.6–91.5] | 96.76 |
| 8 | Al `Alamayn, Muhafazat Matruh, EG | 97.6 [93.0–98.7] | 96.30 | Bi'r al `Abd, Muhafazat Shamal Sina', EG | 85.6 [75.0–90.8] | 96.30 |
| 9 | Arish, Muhafazat Shamal Sina', EG | 97.5 [93.3–98.6] | 95.83 | Gjoa Haven, Nunavut, CA | 85.0 [77.6–89.2] | 95.83 |
| 10 | Bilbays, Eastern Province, EG | 97.3 [90.9–98.8] | 94.91 | Mitzpe Ramon, Southern District, IL | 85.1 [73.6–91.3] | 95.83 |

Control-site ranks (full eligible ordering):

| Control | v6 rank | v9 rank |
|---|---:|---:|
| atacama | 81 | 69 |
| haughton | 33 | 9 |
| meteor_crater | 39 | 33 |

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

v9 is the default because all three pre-registered acceptance criteria pass. Shackleton local/regional and Phoenix use nine features. Arcadia uses eight because curvature fails delivered sensitivity. Jezero regional uses seven because slope_p90 and curvature fail delivered sensitivity. Marius and Jezero local remain unscorable; the new Marius measured-only export explicitly withholds resolution validation. Every feature is included only when its per-feature verdict permits it.
