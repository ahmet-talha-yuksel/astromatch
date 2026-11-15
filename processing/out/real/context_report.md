# Earth annual context — 2025-01..2025-12

24 local MODIS granules opened; original product DOI, grid, file identity and period checked.
All original scoring features, IDs, eligibility decisions and non-context Arrow values/types are preserved.
Monthly extraction: raw/earth_context/2025/monthly_extraction.json (raw cache, excluded from Git).
Minimum 9 quality-accepted months per annual quantity; missing values remain null with reasons.
MODIS CMG 0.05° (~5.55 km at equator); center sampling, cosine-latitude weights, no downscaling.
LST is clear-sky surface overpass temperature, not air temperature or daily Tmax-minus-Tmin.
Day/night differences use paired accepted pixels. Month extrema are extrema of monthly means.
IMERG not supplied; precipitation is null. Unvalidated grid cells are not sampled.

## Non-null annual quantities

| Quantity | Sites / 16 | Grid / 408 |
|---|---:|---:|
| lst_day_mean_c | 0 | 31 |
| lst_night_mean_c | 1 | 3 |
| lst_diurnal_range_c | 0 | 0 |
| lst_min_month_c | 1 | 3 |
| lst_max_month_c | 0 | 31 |
| ndvi_mean | 13 | 202 |
| precip_mm_yr | 0 | 0 |

## Record coverage

| Record | Filled / 7 | Missing-value reasons |
|---|---:|---|
| earth_salda_local | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_kula_local | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_hassa_local | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_atacama_local | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_meke_local | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_tuz_golu_local | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_haughton_local | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 5 < 9 |
| earth_meteor_crater_local | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_salda_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_kula_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_hassa_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_atacama_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_meke_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_tuz_golu_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_haughton_regional | 2/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_meteor_crater_regional | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c410 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c411 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c412 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c413 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r240_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c410 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c411 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c412 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c413 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r241_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r241_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r241_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r241_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r241_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r241_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r242_c410 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r242_c411 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r242_c412 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r242_c413 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 1 < 9; insufficient_valid_months: 2 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r242_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r242_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r242_c416 | 0/7 | cell_not_validated |
| earth_grid_r242_c417 | 0/7 | cell_not_validated |
| earth_grid_r242_c418 | 0/7 | cell_not_validated |
| earth_grid_r242_c419 | 0/7 | cell_not_validated |
| earth_grid_r242_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r242_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r242_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 1 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r242_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 6 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r242_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r242_c425 | 0/7 | cell_not_validated |
| earth_grid_r242_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r242_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r242_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 3 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r242_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r243_c410 | 0/7 | cell_not_validated |
| earth_grid_r243_c411 | 0/7 | cell_not_validated |
| earth_grid_r243_c412 | 0/7 | cell_not_validated |
| earth_grid_r243_c413 | 0/7 | cell_not_validated |
| earth_grid_r243_c414 | 0/7 | cell_not_validated |
| earth_grid_r243_c415 | 0/7 | cell_not_validated |
| earth_grid_r243_c416 | 0/7 | cell_not_validated |
| earth_grid_r243_c417 | 0/7 | cell_not_validated |
| earth_grid_r243_c418 | 0/7 | cell_not_validated |
| earth_grid_r243_c419 | 0/7 | cell_not_validated |
| earth_grid_r243_c420 | 0/7 | cell_not_validated |
| earth_grid_r243_c421 | 0/7 | cell_not_validated |
| earth_grid_r243_c422 | 0/7 | cell_not_validated |
| earth_grid_r243_c423 | 0/7 | cell_not_validated |
| earth_grid_r243_c424 | 0/7 | cell_not_validated |
| earth_grid_r243_c425 | 0/7 | cell_not_validated |
| earth_grid_r243_c426 | 0/7 | cell_not_validated |
| earth_grid_r243_c427 | 0/7 | cell_not_validated |
| earth_grid_r243_c428 | 0/7 | cell_not_validated |
| earth_grid_r243_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 1 < 9; insufficient_valid_months: 2 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r244_c410 | 0/7 | cell_not_validated |
| earth_grid_r244_c411 | 0/7 | cell_not_validated |
| earth_grid_r244_c412 | 0/7 | cell_not_validated |
| earth_grid_r244_c413 | 0/7 | cell_not_validated |
| earth_grid_r244_c414 | 0/7 | cell_not_validated |
| earth_grid_r244_c415 | 0/7 | cell_not_validated |
| earth_grid_r244_c416 | 0/7 | cell_not_validated |
| earth_grid_r244_c417 | 0/7 | cell_not_validated |
| earth_grid_r244_c418 | 0/7 | cell_not_validated |
| earth_grid_r244_c419 | 0/7 | cell_not_validated |
| earth_grid_r244_c420 | 0/7 | cell_not_validated |
| earth_grid_r244_c421 | 0/7 | cell_not_validated |
| earth_grid_r244_c422 | 0/7 | cell_not_validated |
| earth_grid_r244_c423 | 0/7 | cell_not_validated |
| earth_grid_r244_c424 | 0/7 | cell_not_validated |
| earth_grid_r244_c425 | 0/7 | cell_not_validated |
| earth_grid_r244_c426 | 0/7 | cell_not_validated |
| earth_grid_r244_c427 | 0/7 | cell_not_validated |
| earth_grid_r244_c428 | 0/7 | cell_not_validated |
| earth_grid_r244_c429 | 0/7 | cell_not_validated |
| earth_grid_r245_c410 | 0/7 | cell_not_validated |
| earth_grid_r245_c411 | 0/7 | cell_not_validated |
| earth_grid_r245_c412 | 0/7 | cell_not_validated |
| earth_grid_r245_c413 | 0/7 | cell_not_validated |
| earth_grid_r245_c414 | 0/7 | cell_not_validated |
| earth_grid_r245_c415 | 0/7 | cell_not_validated |
| earth_grid_r245_c416 | 0/7 | cell_not_validated |
| earth_grid_r245_c417 | 0/7 | cell_not_validated |
| earth_grid_r245_c418 | 0/7 | cell_not_validated |
| earth_grid_r245_c419 | 0/7 | cell_not_validated |
| earth_grid_r245_c420 | 0/7 | cell_not_validated |
| earth_grid_r245_c421 | 0/7 | cell_not_validated |
| earth_grid_r245_c422 | 0/7 | cell_not_validated |
| earth_grid_r245_c423 | 0/7 | cell_not_validated |
| earth_grid_r245_c424 | 0/7 | cell_not_validated |
| earth_grid_r245_c425 | 0/7 | cell_not_validated |
| earth_grid_r245_c426 | 0/7 | cell_not_validated |
| earth_grid_r245_c427 | 0/7 | cell_not_validated |
| earth_grid_r245_c428 | 0/7 | cell_not_validated |
| earth_grid_r245_c429 | 0/7 | cell_not_validated |
| earth_grid_r246_c410 | 0/7 | cell_not_validated |
| earth_grid_r246_c411 | 0/7 | cell_not_validated |
| earth_grid_r246_c412 | 0/7 | cell_not_validated |
| earth_grid_r246_c413 | 0/7 | cell_not_validated |
| earth_grid_r246_c414 | 0/7 | cell_not_validated |
| earth_grid_r246_c415 | 0/7 | cell_not_validated |
| earth_grid_r246_c416 | 0/7 | cell_not_validated |
| earth_grid_r246_c417 | 0/7 | cell_not_validated |
| earth_grid_r246_c418 | 0/7 | cell_not_validated |
| earth_grid_r246_c419 | 0/7 | cell_not_validated |
| earth_grid_r246_c420 | 0/7 | cell_not_validated |
| earth_grid_r246_c421 | 0/7 | cell_not_validated |
| earth_grid_r246_c422 | 0/7 | cell_not_validated |
| earth_grid_r246_c423 | 0/7 | cell_not_validated |
| earth_grid_r246_c424 | 0/7 | cell_not_validated |
| earth_grid_r246_c425 | 0/7 | cell_not_validated |
| earth_grid_r246_c426 | 0/7 | cell_not_validated |
| earth_grid_r246_c427 | 0/7 | cell_not_validated |
| earth_grid_r246_c428 | 0/7 | cell_not_validated |
| earth_grid_r246_c429 | 0/7 | cell_not_validated |
| earth_grid_r247_c410 | 0/7 | cell_not_validated |
| earth_grid_r247_c411 | 0/7 | cell_not_validated |
| earth_grid_r247_c412 | 0/7 | cell_not_validated |
| earth_grid_r247_c413 | 0/7 | cell_not_validated |
| earth_grid_r247_c414 | 0/7 | cell_not_validated |
| earth_grid_r247_c415 | 0/7 | cell_not_validated |
| earth_grid_r247_c416 | 0/7 | cell_not_validated |
| earth_grid_r247_c417 | 0/7 | cell_not_validated |
| earth_grid_r247_c418 | 0/7 | cell_not_validated |
| earth_grid_r247_c419 | 0/7 | cell_not_validated |
| earth_grid_r247_c420 | 0/7 | cell_not_validated |
| earth_grid_r247_c421 | 0/7 | cell_not_validated |
| earth_grid_r247_c422 | 0/7 | cell_not_validated |
| earth_grid_r247_c423 | 0/7 | cell_not_validated |
| earth_grid_r247_c424 | 0/7 | cell_not_validated |
| earth_grid_r247_c425 | 0/7 | cell_not_validated |
| earth_grid_r247_c426 | 0/7 | cell_not_validated |
| earth_grid_r247_c427 | 0/7 | cell_not_validated |
| earth_grid_r247_c428 | 0/7 | cell_not_validated |
| earth_grid_r247_c429 | 0/7 | cell_not_validated |
| earth_grid_r248_c410 | 0/7 | cell_not_validated |
| earth_grid_r248_c411 | 0/7 | cell_not_validated |
| earth_grid_r248_c412 | 0/7 | cell_not_validated |
| earth_grid_r248_c413 | 0/7 | cell_not_validated |
| earth_grid_r248_c414 | 0/7 | cell_not_validated |
| earth_grid_r248_c415 | 0/7 | cell_not_validated |
| earth_grid_r248_c416 | 0/7 | cell_not_validated |
| earth_grid_r248_c417 | 0/7 | cell_not_validated |
| earth_grid_r248_c418 | 0/7 | cell_not_validated |
| earth_grid_r248_c419 | 0/7 | cell_not_validated |
| earth_grid_r248_c420 | 0/7 | cell_not_validated |
| earth_grid_r248_c421 | 0/7 | cell_not_validated |
| earth_grid_r248_c422 | 0/7 | cell_not_validated |
| earth_grid_r248_c423 | 0/7 | cell_not_validated |
| earth_grid_r248_c424 | 0/7 | cell_not_validated |
| earth_grid_r248_c425 | 0/7 | cell_not_validated |
| earth_grid_r248_c426 | 0/7 | cell_not_validated |
| earth_grid_r248_c427 | 0/7 | cell_not_validated |
| earth_grid_r248_c428 | 0/7 | cell_not_validated |
| earth_grid_r248_c429 | 0/7 | cell_not_validated |
| earth_grid_r249_c410 | 0/7 | cell_not_validated |
| earth_grid_r249_c411 | 0/7 | cell_not_validated |
| earth_grid_r249_c412 | 0/7 | cell_not_validated |
| earth_grid_r249_c413 | 0/7 | cell_not_validated |
| earth_grid_r249_c414 | 0/7 | cell_not_validated |
| earth_grid_r249_c415 | 0/7 | cell_not_validated |
| earth_grid_r249_c416 | 0/7 | cell_not_validated |
| earth_grid_r249_c417 | 0/7 | cell_not_validated |
| earth_grid_r249_c418 | 0/7 | cell_not_validated |
| earth_grid_r249_c419 | 0/7 | cell_not_validated |
| earth_grid_r249_c420 | 0/7 | cell_not_validated |
| earth_grid_r249_c421 | 0/7 | cell_not_validated |
| earth_grid_r249_c422 | 0/7 | cell_not_validated |
| earth_grid_r249_c423 | 0/7 | cell_not_validated |
| earth_grid_r249_c424 | 0/7 | cell_not_validated |
| earth_grid_r249_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r249_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r249_c427 | 0/7 | cell_not_validated |
| earth_grid_r249_c428 | 0/7 | cell_not_validated |
| earth_grid_r249_c429 | 0/7 | cell_not_validated |
| earth_grid_r250_c410 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r250_c411 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r250_c412 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r250_c413 | 0/7 | cell_not_validated |
| earth_grid_r250_c414 | 0/7 | cell_not_validated |
| earth_grid_r250_c415 | 0/7 | cell_not_validated |
| earth_grid_r250_c416 | 0/7 | cell_not_validated |
| earth_grid_r250_c417 | 0/7 | cell_not_validated |
| earth_grid_r250_c418 | 0/7 | cell_not_validated |
| earth_grid_r250_c419 | 0/7 | cell_not_validated |
| earth_grid_r250_c420 | 0/7 | cell_not_validated |
| earth_grid_r250_c421 | 0/7 | cell_not_validated |
| earth_grid_r250_c422 | 0/7 | cell_not_validated |
| earth_grid_r250_c423 | 0/7 | cell_not_validated |
| earth_grid_r250_c424 | 0/7 | cell_not_validated |
| earth_grid_r250_c425 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 6 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r250_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r250_c427 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 6 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r250_c428 | 0/7 | cell_not_validated |
| earth_grid_r250_c429 | 0/7 | cell_not_validated |
| earth_grid_r251_c410 | 0/7 | cell_not_validated |
| earth_grid_r251_c411 | 0/7 | cell_not_validated |
| earth_grid_r251_c412 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r251_c413 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 3 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r251_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r251_c415 | 0/7 | cell_not_validated |
| earth_grid_r251_c416 | 0/7 | cell_not_validated |
| earth_grid_r251_c417 | 0/7 | cell_not_validated |
| earth_grid_r251_c418 | 0/7 | cell_not_validated |
| earth_grid_r251_c419 | 0/7 | cell_not_validated |
| earth_grid_r251_c420 | 0/7 | cell_not_validated |
| earth_grid_r251_c421 | 0/7 | cell_not_validated |
| earth_grid_r251_c422 | 0/7 | cell_not_validated |
| earth_grid_r251_c423 | 0/7 | cell_not_validated |
| earth_grid_r251_c424 | 0/7 | cell_not_validated |
| earth_grid_r251_c425 | 0/7 | cell_not_validated |
| earth_grid_r251_c426 | 0/7 | cell_not_validated |
| earth_grid_r251_c427 | 0/7 | cell_not_validated |
| earth_grid_r251_c428 | 0/7 | cell_not_validated |
| earth_grid_r251_c429 | 0/7 | cell_not_validated |
| earth_grid_r252_c410 | 0/7 | cell_not_validated |
| earth_grid_r252_c411 | 0/7 | cell_not_validated |
| earth_grid_r252_c412 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r252_c413 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9; insufficient_valid_months: 3 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r252_c414 | 0/7 | cell_not_validated |
| earth_grid_r252_c415 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 6 < 9 |
| earth_grid_r252_c416 | 0/7 | cell_not_validated |
| earth_grid_r252_c417 | 0/7 | cell_not_validated |
| earth_grid_r252_c418 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 7 < 9 |
| earth_grid_r252_c419 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 7 < 9 |
| earth_grid_r252_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r252_c421 | 0/7 | cell_not_validated |
| earth_grid_r252_c422 | 0/7 | cell_not_validated |
| earth_grid_r252_c423 | 0/7 | cell_not_validated |
| earth_grid_r252_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r252_c425 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r252_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r252_c427 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r252_c428 | 0/7 | cell_not_validated |
| earth_grid_r252_c429 | 0/7 | cell_not_validated |
| earth_grid_r253_c410 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r253_c411 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r253_c412 | 2/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r253_c413 | 4/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r253_c414 | 5/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 8 < 9 |
| earth_grid_r253_c415 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 6 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r253_c416 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9 |
| earth_grid_r253_c417 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r253_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 1 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r253_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r253_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r253_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r253_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r253_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 6 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r253_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 1 < 9; insufficient_valid_months: 2 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r253_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r253_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r253_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r253_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r253_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r254_c410 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r254_c411 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r254_c412 | 2/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 3 < 9 |
| earth_grid_r254_c413 | 2/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r254_c414 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r254_c415 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9 |
| earth_grid_r254_c416 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9 |
| earth_grid_r254_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r254_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r254_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r254_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r254_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c410 | 0/7 | cell_not_validated |
| earth_grid_r255_c411 | 0/7 | cell_not_validated |
| earth_grid_r255_c412 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 7 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r255_c413 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r255_c414 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9 |
| earth_grid_r255_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r255_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r255_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r255_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r255_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r255_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r255_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r256_c410 | 0/7 | cell_not_validated |
| earth_grid_r256_c411 | 0/7 | cell_not_validated |
| earth_grid_r256_c412 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9 |
| earth_grid_r256_c413 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 6 < 9 |
| earth_grid_r256_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9 |
| earth_grid_r256_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r256_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r256_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r256_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 2 < 9 |
| earth_grid_r256_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r256_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r256_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r256_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c410 | 0/7 | cell_not_validated |
| earth_grid_r257_c411 | 0/7 | cell_not_validated |
| earth_grid_r257_c412 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9 |
| earth_grid_r257_c413 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9 |
| earth_grid_r257_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 3 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r257_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r257_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r257_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 2 < 9 |
| earth_grid_r258_c410 | 0/7 | cell_not_validated |
| earth_grid_r258_c411 | 0/7 | cell_not_validated |
| earth_grid_r258_c412 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 7 < 9 |
| earth_grid_r258_c413 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 6 < 9 |
| earth_grid_r258_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r258_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r258_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r258_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r258_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r258_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r259_c410 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r259_c411 | 0/7 | cell_not_validated |
| earth_grid_r259_c412 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 3 < 9; insufficient_valid_months: 4 < 9 |
| earth_grid_r259_c413 | 3/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 1 < 9; insufficient_valid_months: 2 < 9 |
| earth_grid_r259_c414 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c415 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c416 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c417 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c418 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r259_c419 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 2 < 9 |
| earth_grid_r259_c420 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c421 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c422 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r259_c423 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c424 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c425 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c426 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c427 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r259_c428 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r259_c429 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9; insufficient_valid_months: 1 < 9 |
| earth_grid_r130_c220 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r130_c221 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r131_c220 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r131_c221 | 1/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 0 < 9 |
| earth_grid_r308_c320 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 8 < 9 |
| earth_grid_r308_c321 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 3 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 7 < 9 |
| earth_grid_r309_c320 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 4 < 9; insufficient_valid_months: 6 < 9 |
| earth_grid_r309_c321 | 0/7 | input_not_supplied: GPM_3IMERGM v07 monthly files; insufficient_valid_months: 2 < 9; insufficient_valid_months: 5 < 9; insufficient_valid_months: 6 < 9 |

## Original products

Each input hash and processing policy is in context_provenance.json.
- https://doi.org/10.5067/MODIS/MOD11C3.061
- https://doi.org/10.5067/MODIS/MOD13C2.061
- https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11C3
- https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13C2
