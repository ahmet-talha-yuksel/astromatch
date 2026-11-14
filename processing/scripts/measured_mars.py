"""Measured-only Mars regional estimator and user-approved engineering sensitivity gate."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import tempfile

import numpy as np
import rasterio

from .dem import DemRequest, process_dem
from .metrics import TOPOGRAPHIC, feature
from .generate_mock import write_json
from .process_dem import export_heightmap

METHOD = 'measured_only_planefit_v1'
ABS = dict(zip(TOPOGRAPHIC, (.2, .2, .05, 2., 10., 5.)))
THRESHOLDS = {'rel': .15, 'abs': ABS, 'max_effective_nodata': .30}


def metrics(array, spacing=1000):
    """6/9 finite samples; clipped edges; Riley sum over measured neighbors only.

    TRI requires an observed center (no synthetic center elevation). Plane-fit
    slope may be evaluated at a missing center when six surrounding bins exist.
    """
    z = np.asarray(array, dtype=float)
    if z.ndim != 2 or min(z.shape) < 3 or not np.isfinite(spacing) or spacing <= 0:
        raise ValueError('Expected 2D grid >=3x3 and positive spacing')
    pad = np.pad(z, 1, constant_values=np.nan)
    slopes, tris = [], []
    yy, xx = np.mgrid[-1:2, -1:2]
    design = np.column_stack((xx.ravel()*spacing, yy.ravel()*spacing, np.ones(9)))
    for row, col in np.ndindex(z.shape):
        patch = pad[row:row+3, col:col+3].ravel()
        valid = np.isfinite(patch)
        if valid.sum() < 6:
            continue
        coeff, _, rank, _ = np.linalg.lstsq(design[valid], patch[valid], rcond=None)
        if rank != 3:
            continue
        slopes.append(np.degrees(np.arctan(np.hypot(*coeff[:2]))))
        if np.isfinite(patch[4]):
            tris.append(np.sqrt(np.sum((patch[valid]-patch[4])**2)))
    observed = z[np.isfinite(z)]
    values = [float(np.median(slopes)) if slopes else None,
              float(np.percentile(slopes, 90)) if slopes else None,
              float(np.mean(np.asarray(slopes) < 5)) if slopes else None,
              float(np.median(tris)) if tris else None,
              float(np.percentile(observed,95)-np.percentile(observed,5)) if observed.size else None,
              float(observed.std()) if observed.size else None]
    return dict(zip(TOPOGRAPHIC, values)), 1-len(slopes)/z.size


def sensitivity(measured, interpolated):
    result = {}
    for key in TOPOGRAPHIC:
        a, b = measured[key], interpolated[key]
        diff = abs(a-b) if a is not None and b is not None else None
        rel = diff/abs(b) if diff is not None and b != 0 else (0. if diff == 0 else None)
        result[key] = {'abs_diff': diff, 'rel_diff': rel,
                       'pass': bool(diff is not None and (diff <= ABS[key] or (rel is not None and rel <= .15)))}
    return result


def evaluate(request):
    if request.body != 'mars' or request.scale != 'regional' or not request.counts_path:
        raise ValueError('Only regional Mars with measured-bin mask is supported')
    request = replace(request, analysis_resolution_m=1000)
    record, control = process_dem(request)
    if abs(record['provenance']['source_radius_m']-3396000) > .001:
        raise ValueError('Mars sphere must be 3396000 m')
    with rasterio.open(request.path) as src, rasterio.open(request.counts_path) as counts:
        if src.shape != counts.shape or src.transform != counts.transform or src.crs != counts.crs:
            raise ValueError('Elevation/count grids must match')
        heights = src.read(1, masked=True).astype('float64').filled(np.nan)
        support = counts.read(1, masked=True).filled(0) > 0
        heights[~support] = np.nan
        profile = src.profile.copy(); profile.update(dtype='float64', nodata=np.nan)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'measured.tif'
            with rasterio.open(path, 'w', **profile) as dst:
                dst.write(heights, 1); dst.scales=src.scales; dst.offsets=src.offsets
                if src.units[0]: dst.set_band_unit(1,src.units[0])
            _, measured = process_dem(replace(request, path=str(path)))
    primary, effective = metrics(measured)
    interpolated, _ = metrics(control)
    checks = sensitivity(primary, interpolated)
    passed = all(c['pass'] for c in checks.values()) and effective <= .30 and request.georeferencing_verified and not request.synthetic
    raw = float(1-np.isfinite(measured).mean())
    failed = [key for key, c in checks.items() if not c['pass']]
    reasons = ([f'Sensitivity thresholds exceeded or metric missing: {", ".join(failed)}'] if failed else [])
    if effective > .30: reasons.append('Effective NoData exceeds 0.30')
    if not request.georeferencing_verified: reasons.append('Georeferencing unverified')
    if request.synthetic: reasons.append('Synthetic source')
    record.update(method=METHOD, dem_source='MOLA MEGDR + measured-bin mask',
                  resolution_validated=bool(passed),
                  features={k:feature(v, validated=passed, status='derived') for k,v in primary.items()},
                  features_interpolated=interpolated,
                  measurement_support={'raw_unmeasured_ratio':raw, 'effective_nodata_ratio':effective,
                      'min_measured_neighbors':6, 'sensitivity':checks, 'thresholds':THRESHOLDS,
                      'validation_basis':'User-approved engineering sensitivity threshold; same observations, not independent accuracy validation',
                      'raw_ratio_definition':'Analysis cells with no measured source-bin contribution / all analysis cells',
                      'tri_definition':'Riley sqrt(sum squared differences), measured neighbors only, measured center required',
                      'edge_rule':'Outside window is NoData; six measured samples still required',
                      'unscorable_reasons':reasons})
    record['quality'].update(nodata_ratio=effective, coverage='partial' if effective else 'full',
        validation_eligible=bool(passed), warnings=[f'measured-only; raw unmeasured {raw:.2%}; '+
            ('all features within sensitivity thresholds' if not failed else '; '.join(reasons)),
            'Engineering sensitivity validation; not independent accuracy or landing suitability validation.'])
    record['provenance'].update(max_nodata_ratio=.30, validation_policy=METHOD,
        counts_file_sha256=__import__('hashlib').sha256(Path(request.counts_path).read_bytes()).hexdigest())
    return record, measured


def run(site, root):
    root=Path(root).resolve()
    if site == 'jezero':
        item=next(r for r in json.loads((root/'configs/salda_jezero.real.json').read_text())['records'] if r['region_id']=='mars_jezero_regional')
        for key in ('path','counts_path'): item[key]=str((root/'configs'/item[key]).resolve())
    else:
        prior=next(r for r in json.loads((root/'out/mars_candidates/features.json').read_text())['records'] if r['region_id']==f'mars_{site}_regional')
        item={k:prior[k] for k in ('region_id','name','body','lat','lon','scale','source_resolution_m','dem_version')}
        item.update(path=str(root/f'raw/mars_candidates/{site}_topography.tif'),counts_path=str(root/f'raw/mars_candidates/{site}_counts.tif'), product='mola',vertical_unit='m',vertical_reference=prior['provenance']['vertical_reference'],source_url=prior['provenance']['source_url'],accessed_on=prior['provenance']['accessed_on'],georeferencing_verified=True)
    record,array=evaluate(DemRequest(**item))
    record['target_id']={'phoenix':'T-04','jezero':'T-01','arcadia':'T-05'}[site]
    output=root/'out/mars_measured'; output.mkdir(exist_ok=True)
    export_heightmap(output,record,array)
    path=output/'features.json'
    payload=json.loads(path.read_text()) if path.exists() else {'schema_version':'2.3','records':[]}
    payload['records']=[r for r in payload['records'] if r['region_id'] != record['region_id']]+[record]
    write_json(path,payload)
    print(json.dumps({'region_id':record['region_id'],'validated':record['resolution_validated'],'support':record['measurement_support']},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site',choices=['phoenix','jezero','arcadia'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();run(args.site,args.root)
