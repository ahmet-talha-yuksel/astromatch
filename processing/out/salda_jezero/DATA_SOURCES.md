# DEM batch provenance

Synthetic fixtures are not NASA/ESA observations. No downloads were performed by this pipeline.

Parameters and CRS are also stored in features.json.

## earth_salda_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile last-modified 2022-05-09
- Source: https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N37_00_E029_00_DEM/Copernicus_DSM_COG_10_N37_00_E029_00_DEM.tif
- Accessed on (declared): 2026-11-14
- Input: salda_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## mars_jezero_local

- Status: derived; synthetic: False
- Product/version: mola / MGS-M-MOLA-5-MEGDR-L3-V1.0; product version 2.0
- Source: https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.img
- Accessed on (declared): 2026-11-14
- Input: jezero_mola_topography.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: GMM3 (mgm1025) degree/order 50 areoid

## earth_salda_regional

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile last-modified 2022-05-09
- Source: https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N37_00_E029_00_DEM/Copernicus_DSM_COG_10_N37_00_E029_00_DEM.tif
- Accessed on (declared): 2026-11-14
- Input: salda_glo30.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## mars_jezero_regional

- Status: derived; synthetic: False
- Product/version: mola / MGS-M-MOLA-5-MEGDR-L3-V1.0; product version 2.0
- Source: https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.img
- Accessed on (declared): 2026-11-14
- Input: jezero_mola_topography.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: GMM3 (mgm1025) degree/order 50 areoid
