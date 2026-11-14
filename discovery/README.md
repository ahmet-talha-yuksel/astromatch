# AstroMatch AI — USGS analog dataset preparation

**Branch:** `feature/discovery`  
**Folder:** `discovery/`  
**Dataset:** USGS *Known Terrestrial Analog Sites for Planetary Science*  
**DOI:** https://doi.org/10.5066/P9J72921  
**ScienceBase item:** `5f88940b82cebb8c13d912ee`

## Important scope note

This USGS release is a **known-site point layer** (examples described by USGS include impact craters, dunes, volcanoes, and other planetary-relevant processes). It is a validation/reference dataset. It is **not** the 0.5° global candidate grid and should not be treated as a complete inventory of every Earth analog.

The source download could not be retrieved in the current ChatGPT execution environment because the official ScienceBase/USGS endpoints returned access errors. Therefore no row count, field list, or cleaned output is claimed here. Run the script from your local machine to fetch and process the actual source.

## Setup

From the repository root:

```bash
git switch -c feature/discovery
mkdir -p discovery
# Copy this package's contents into discovery/

cd discovery
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python fetch_usgs_analogs.py
```

## Outputs

After a successful run:

```text
discovery/
├── fetch_usgs_analogs.py
├── requirements.txt
├── README.md
└── data/
    ├── raw/
    │   ├── usgs_analogs_source.zip
    │   └── extracted/
    └── processed/
        ├── usgs_analogs_clean.geojson
        ├── usgs_analogs_clean.csv
        └── cleaning_report.json
```

## Cleaning rules

1. Download item metadata and all attached ScienceBase files.
2. Extract the source archive safely.
3. Find a supported vector dataset (`.gpkg`, `.geojson`, `.json`, `.shp`, `.kml`, `.gml`).
4. Reject missing CRS instead of guessing it.
5. Reproject to `EPSG:4326`.
6. Remove null/empty geometries and impossible WGS84 bounds.
7. Remove exact duplicate geometries.
8. Preserve all original attributes.
9. Add normalized fields only when a source field can be mapped conservatively.
10. Derive point longitude/latitude from geometry, not potentially stale attribute values.
11. Write GeoJSON, CSV, and a machine-readable cleaning report.

## Important scientific safeguards

- Do not infer a planetary target body from a landform name.
- Do not fill missing analog types with guessed categories.
- Do not assume the USGS points cover all relevant analog sites.
- Keep source record IDs and the DOI in downstream records.
- Use this set for a known-site validation check, not as training truth for the global similarity ranking.
- Keep `global_candidates.geojson` (generated from the global 0.5° grid) separate from the known-site validation layer.

## Suggested integration contract

The output GeoJSON retains original fields and adds:

| Field | Meaning |
|---|---|
| `astromatch_source` | Stable source label |
| `source_doi` | Original DOI |
| `source_item_id` | ScienceBase item identifier |
| `source_record_id` | Deterministic ID for this export |
| `name` | Mapped site name, if present |
| `analog_type` | Mapped analog type, if present |
| `target_body` | Mapped planetary target, if present |
| `longitude` | WGS84 longitude for point geometries |
| `latitude` | WGS84 latitude for point geometries |

Do not change the team's shared JSON schema without approval. If the team schema differs, write a small adapter rather than changing this source-preserving output.

## Source citation

Hunter, M.A. (2020). *Known Terrestrial Analog Sites for Planetary Science*. U.S. Geological Survey data release. https://doi.org/10.5066/P9J72921


## Known analogs

`known_analogs.json` adapts the cleaned USGS point records without changing the shared JSON schema. Cell IDs use the containing 0.5-degree latitude/longitude cell, formatted as `g_{lat:06.2f}_{lon:06.2f}`; each value is the cell center (for example, `g_037.75_029.75`).

`analog_for` is `mars` or `moon` only when the source `AnalogBody` says Mars or Moon. It remains an empty list when the source body is blank or missing; no target is inferred.

The USGS list has 190 impact crater records out of 192, so validation is crater-weighted.


## Turkey analogs

`out/turkey_analogs.json` records the six supplied Turkish field sites as qualitative candidate/reference hypotheses and links each to `features.json` by `region_id`. It uses the `0.1-draft` schema, `draft_qualitative` status, approximate unverified coordinates, qualitative tags/dimensions, and no numeric terrain or climate features.

Matches are qualitative hypotheses; ranking comes from Person 2's similarity engine. Meke and Acıgöl share the same global 0.5° cell (`g_037.75_033.75`) and reference each other through `shares_cell_with`. Hassa's longitude is on a cell boundary at approximately 36.5°; its current cell is computed from the supplied coordinate and must be recalculated when the coordinate is confirmed.

### Bilinen sorunlar

USGS-ANALOG-00136 (Ritland) attribute and geometry coordinates differ by approximately 1.3 km; the geometry coordinate was used. `analog_mapping.cell_id` gives `g_064.75_-16.25` for geometry (64.92813695180274, -16.4958615463001), and `g_064.75_-16.75` for attributes (64.9321, -16.5217).


## Validation and stability

The validation, stability and export outputs include a `scope` block with processed/valid cell counts, latitude/longitude ranges, the ten most populated 5-degree bins, source branch/commit from `data/inputs/SOURCE.txt`, and the note that coverage is not global. Cell joins use coordinate-derived `cell_key` values; grid `region_id` values are not treated as cell keys.

Only `slope_median_deg`, `slope_p90_deg`, `flat_fraction`, `tri_median_m`, `relief_m`, and `elevation_std_m` enter scoring or stability noise. NDVI and precipitation are filters when supplied; temperature does not enter the score.

For USGS validation, positives are cells containing listed analogs. The primary comparison set is all valid cells without a listed analog; this is unlabeled background, not confirmed negative examples. The sensitivity comparison removes the eight neighboring cells of positives from that background. AUC uses average ranks for ties; bootstrap intervals resample positive and background scores independently; permutation p-values shuffle class membership. Percentile is the positive-cell average rank among valid cells, with the highest rank at 100. Top 1%/5% enrichment compares positive share in each ranked slice with overall positive prevalence.

T-01 and T-03 are unscorable and have null metrics with an `unscorable` reason. T-02 is the only target currently scored. If positive counts are below the configured minimum, metric tests are skipped and positive names, scores, and percentiles are reported descriptively. Caveats: 190/192 USGS records are impact craters; `analog_for` is blank for 191 records, so targets share the same positive cells; background is unlabeled; Atacama and Turkish sites are absent from the USGS list; this does not establish volcanic or carbonate analog evidence.

Stability noise is Gaussian at 1%, 5%, and 10% of each scoring feature's standard deviation, clipped to physical bounds. `end_to_end` lets the ranker recompute sigma; `frozen` calls the ranker with `sigma="frozen"`. Run the two modes separately and compare their separate result files.


### Feature and grid coverage links (schema 0.2-draft)

Turkey records link to the actual local and regional `features.json` records when both scales exist. Each record's `feature_availability` contains only `resolution_validated`, the count of comparable scoring metrics (out of six), and `data_status`; numerical feature values remain in `features.json`. `grid_coverage` is derived from the coordinate cell key against the processed grid and coverage report. The source commit is copied from `data/inputs/SOURCE.txt`. Acigol has no separate feature record and shares Meke's 0.5-degree cell; Hassa's cell is marked `not_scanned` in the supplied grid coverage.
