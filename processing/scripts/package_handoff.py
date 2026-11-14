"""Create a small, deterministic consumer bundle; raw NASA/ESA files are excluded."""
import argparse
import json
from pathlib import Path
import zipfile


def package(source,output):
    source,output=Path(source),Path(output)
    records=json.loads((source/'features.json').read_text())['records']
    allowed=[source/name for name in ('features.json','earth_grid.parquet','coverage.geojson','DATA_SOURCES.md')]
    for directory in ('heightmaps','quality'):
        if (source/directory).exists():allowed.extend(p for p in (source/directory).rglob('*') if p.is_file())
    readme=('AstroMatch AI v2.3 — Similarity Engine input\n\n'
            f'Records: {len(records)}. Topographic QA-qualified records: {sum(r["resolution_validated"] for r in records)}.\n'
            'Read features.json["records"]. Each metric is {value, data_status, comparable}.\n'
            'A pair must match scale, window_km, analysis_resolution_m and method; both values must be non-null and comparable=true.\n'
            'Use slope_median_deg, slope_p90_deg, flat_fraction, tri_median_m, relief_m, elevation_std_m.\n'
            'earth_filters (including NDVI/land fraction) are not scoring features. Missing values are null, not zero.\n'
            'Current approved target: Shackleton. Jezero and Marius Hills remain unapproved until their stated quality gaps are resolved.\n'
            'Operational QA is not independent absolute accuracy or mission suitability validation.\n'
            'Global discovery grid is a separate processing/out/pilot delivery. This bundle includes curated Earth sites.\n'
            'No raw rasters, account credentials, ranking implementation or frontend changes are included.\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(allowed):
            info=zipfile.ZipInfo(str(path.relative_to(source)),date_time=(2026,1,1,0,0,0))
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
