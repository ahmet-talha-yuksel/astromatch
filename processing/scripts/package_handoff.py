"""Create a small, deterministic consumer bundle; raw NASA/ESA files are excluded."""
import argparse
import json
from pathlib import Path
import zipfile


def package(source,output):
    source,output=Path(source),Path(output)
    records=json.loads((source/'features.json').read_text())['records']
    allowed=[source/name for name in ('features.json','earth_grid.parquet','coverage.geojson','DATA_SOURCES.md')]
    for name in ('environment.json','target_quality.json'):
        if (source/name).exists():allowed.append(source/name)
    for directory in ('heightmaps','quality'):
        if (source/directory).exists():allowed.extend(p for p in (source/directory).rglob('*') if p.is_file())
    entries = [(path, str(path.relative_to(source))) for path in allowed]
    # Keep measured-only exports separate from the curated release and its QA hash.
    for folder in ('mars_measured', 'moon_measured'):
        target = source.parent/folder
        if not (target/'features.json').is_file(): continue
        payload = json.loads((target/'features.json').read_text())
        names = {'features.json'}
        if (target/'DATA_SOURCES.md').exists(): names.add('DATA_SOURCES.md')
        for record in payload['records']:
            names.update(record['heightmap'][key] for key in ('path','metadata_path'))
        for name in sorted(names):
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or not (target/path).is_file():
                raise ValueError('Unsafe or missing measured-target bundle reference')
            entries.append((target/path, f'{folder}/{path}'))
    readme=('AstroMatch AI v2.3 — Similarity Engine input\n\n'
            f'Records: {len(records)}. Topographic QA-qualified records: {sum(r["resolution_validated"] for r in records)}.\n'
            'Read features.json["records"]. Each metric is {value, data_status, comparable}.\n'
            'A pair must match scale, window_km, analysis_resolution_m and method; both values must be non-null and comparable=true.\n'
            'Use slope_median_deg, slope_p90_deg, flat_fraction, tri_median_m, relief_m, elevation_std_m.\n'
            'Additional data-only descriptors: hypsometric_integral, roughness_ratio, curvature_std_per_km. Existing scores and six-metric QA decisions are unchanged.\n'
            'Morphology uses measured source samples only (counts > 0 before reprojection for Mars/Moon); quality.morphology records window, support, method and null reasons.\n'
            'Roughness is median paired population std(3x3)/std(15x15), with at least 6/9 and 150/225 measured samples. Curvature is std of quadratic-fit elevation Laplacian, in km^-1.\n'
            'Finite morphology values are derived/comparable; undefined ratios or insufficient support remain null/comparable=false. These flags do not promote a record for scoring.\n'
            'Measured-target subfolders, when present, contain nine interpolated controls and nine sensitivity checks: <=15% relative difference OR absolute HI 0.02, roughness ratio 0.05, curvature 0.01 km^-1. Failed descriptors have comparable=false.\n'
            'measurement_support.validation_features identifies the legacy six-feature gate; all_nine_sensitivity_passed and nine_feature_validation_passed distinguish nine checks from record approval. Curated QA decisions remain unchanged; Marius measured-only is a separate unpromoted candidate.\n'
            'earth_filters (including NDVI/land fraction) are not scoring features. Missing values are null, not zero.\n'
            'Monthly MODIS overpass temperatures are contextual; their day/night difference is not daily Tmax-minus-Tmin and is not score-ready.\n'
            'Current approved target: Shackleton. Jezero and Marius Hills remain unapproved until their stated quality gaps are resolved.\n'
            'Operational QA is not independent absolute accuracy or mission suitability validation.\n'
            'Discovery uses processing/out/earth_grid.parquet and coverage.geojson. This bundle includes curated Earth sites; its Parquet is not the discovery scan.\n'
            'No raw rasters, account credentials, ranking implementation or frontend changes are included.\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path, name in sorted(entries, key=lambda entry: entry[1]):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,path.read_bytes())
        info=zipfile.ZipInfo('HANDOFF.md',date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,readme)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('processing/out/real'))
    parser.add_argument('--output',type=Path,default=Path('processing/out/handoff/kisi2_v2_3.zip'))
    args=parser.parse_args();print(package(args.source,args.output))
