"""Measured-only planetary regional estimator and engineering sensitivity checks."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import tempfile

import numpy as np
import rasterio

from .dem import DemRequest, process_dem
from .metrics import TOPOGRAPHIC, feature
from .morphology import MORPHOLOGY, morphology_features
from .morphology_quality import annotate_zero_roughness
from .generate_mock import write_json
from .process_dem import export_heightmap

METHOD = 'measured_only_planefit_v1'
ABS = dict(zip(TOPOGRAPHIC, (.2, .2, .05, 2., 10., 5.)))
ABS.update(hypsometric_integral=.02, roughness_ratio=.05, curvature_std_per_km=.01)
MEASURED_FEATURES = (*TOPOGRAPHIC, *MORPHOLOGY)
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


def sensitivity(measured, interpolated, *, keys=MEASURED_FEATURES):
    result = {}
    for key in keys:
        a, b = measured.get(key), interpolated.get(key)
        a = a if a is not None and np.isfinite(a) else None
        b = b if b is not None and np.isfinite(b) else None
        diff = abs(a-b) if a is not None and b is not None else None
        rel = diff/abs(b) if diff is not None and b != 0 else (0. if diff == 0 else None)
        result[key] = {'abs_diff': diff, 'rel_diff': rel,
                       'pass': bool(diff is not None and (diff <= ABS[key] or (rel is not None and rel <= .15)))}
    return result


def add_morphology_sensitivity(record, control):
    """Extend an existing measured record without altering its six-metric gate."""
    extra, _ = morphology_features(control, record['analysis_resolution_m'])
    record['features_interpolated'].update({k: extra[k]['value'] for k in MORPHOLOGY})
    primary = {k: record['features'][k]['value'] for k in MEASURED_FEATURES}
    checks = sensitivity(primary, record['features_interpolated'])
    support = record['measurement_support']
    support['sensitivity'] = checks
    support['thresholds'] = THRESHOLDS
    support['validation_features'] = list(TOPOGRAPHIC)
    support['all_nine_sensitivity_passed'] = all(c['pass'] for c in checks.values())
    support['nine_feature_validation_passed'] = bool(record['resolution_validated'] and all(c['pass'] for c in checks.values()))
    support['morphology_sensitivity_policy'] = {
        'version': 'measured-only-morphology-sensitivity-v1',
        'rule': 'abs_diff <= absolute tolerance OR rel_diff <= 0.15; relative baseline is interpolated',
        'curvature_absolute_unit': 'km^-1',
        'curvature_absolute_rationale': 'Engineering tolerance 0.01 km^-1, equivalent to a 10 m Laplacian numerator at 1000 m spacing; not independently calibrated accuracy.',
        'scope': 'New descriptors are checked individually; legacy six-feature approval and scoring weights are unchanged.',
        'failed_features': [k for k in MORPHOLOGY if not checks[k]['pass']],
    }
    for key in MORPHOLOGY:
        record['features'][key]['comparable'] = bool(checks[key]['pass'] and not record.get('synthetic'))
    record['quality']['morphology']['comparability_basis'] = 'finite measured value and per-feature absolute-or-relative sensitivity pass; record quality gate still applies'
    prefix = 'Morphology sensitivity failed: '
    warnings = record['quality']['warnings']
    warnings[:] = [w for w in warnings if not w.startswith(prefix)]
    failed = support['morphology_sensitivity_policy']['failed_features']
    if failed: warnings.append(prefix + ', '.join(failed) + '; those descriptors are not comparable. Legacy six-feature approval is unchanged.')
    annotate_zero_roughness(record)
    return record


def evaluate(request):
    if request.body not in ('mars', 'moon') or request.scale != 'regional' or not request.counts_path:
        raise ValueError('Only regional Mars/Moon with measured-bin mask is supported')
    request = replace(request, analysis_resolution_m=1000)
    record, control = process_dem(request)
    radius = 3396000 if request.body == 'mars' else 1737400
    if abs(record['provenance']['source_radius_m']-radius) > .001:
        raise ValueError(f'{request.body} sphere must be {radius} m')
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
    extra, morphology_support = morphology_features(measured, request.analysis_resolution_m,
        status='mock' if request.synthetic else 'derived', comparable=not request.synthetic)
    morphology_support["source_support"] = "counts > 0 before reprojection"
    primary, effective = metrics(measured)
    interpolated, _ = metrics(control)
    checks = sensitivity(primary, interpolated, keys=TOPOGRAPHIC)
    passed = all(c['pass'] for c in checks.values()) and effective <= .30 and request.georeferencing_verified and not request.synthetic
    raw = float(1-np.isfinite(measured).mean())
    failed = [key for key, c in checks.items() if not c['pass']]
    reasons = ([f'Sensitivity thresholds exceeded or metric missing: {", ".join(failed)}'] if failed else [])
    if effective > .30: reasons.append('Effective NoData exceeds 0.30')
    if not request.georeferencing_verified: reasons.append('Georeferencing unverified')
    if request.synthetic: reasons.append('Synthetic source')
    if request.body == 'moon':
        passed = False
        reasons.append('Measured-only lunar candidate; existing LOLA scoring approval is not promoted by this export.')
    record.update(method=METHOD, dem_source=('MOLA MEGDR' if request.body == 'mars' else 'LOLA GDR')+' + measured-bin mask',
                  resolution_validated=bool(passed),
                  features={**{k:feature(v, validated=passed, status='derived') for k,v in primary.items()}, **extra},
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
            ('all six legacy features within sensitivity thresholds' if not reasons else '; '.join(reasons)),
            'Engineering sensitivity validation; not independent accuracy or landing suitability validation.'])
    record['quality']['morphology'] = morphology_support
    record['provenance'].update(max_nodata_ratio=.30, validation_policy=METHOD,
        counts_file_sha256=__import__('hashlib').sha256(Path(request.counts_path).read_bytes()).hexdigest())
    add_morphology_sensitivity(record, control)
    if request.body == 'moon':
        record['measurement_support']['validation_basis'] = 'Engineering sensitivity checks only; no lunar scoring approval or independent accuracy validation'
        record['quality']['warnings'].append('Regional context only: a 1000 m grid cannot resolve the roughly 50 m Marius pit entrance.')
    return record, measured


def request_for(site, root):
    root=Path(root).resolve()
    if site in ('jezero', 'marius'):
        config = 'salda_jezero.real.json' if site == 'jezero' else 'marius.real.json'
        region = 'mars_jezero_regional' if site == 'jezero' else 'moon_marius_hills_regional'
        item=next(r for r in json.loads((root/'configs'/config).read_text())['records'] if r['region_id']==region)
        for key in ('path','counts_path'): item[key]=str((root/'configs'/item[key]).resolve())
    else:
        prior=next(r for r in json.loads((root/'out/mars_candidates/features.json').read_text())['records'] if r['region_id']==f'mars_{site}_regional')
        item={k:prior[k] for k in ('region_id','name','body','lat','lon','scale','source_resolution_m','dem_version')}
        item.update(path=str(root/f'raw/mars_candidates/{site}_topography.tif'),counts_path=str(root/f'raw/mars_candidates/{site}_counts.tif'), product='mola',vertical_unit='m',vertical_reference=prior['provenance']['vertical_reference'],source_url=prior['provenance']['source_url'],accessed_on=prior['provenance']['accessed_on'],georeferencing_verified=True)
    return DemRequest(**item)


def run(site, root):
    root=Path(root).resolve()
    record,array=evaluate(request_for(site, root))
    record['target_id']={'phoenix':'T-04','jezero':'T-01','arcadia':'T-05','marius':'T-03'}[site]
    output=root/('out/moon_measured' if site == 'marius' else 'out/mars_measured'); output.mkdir(exist_ok=True)
    export_heightmap(output,record,array)
    path=output/'features.json'
    payload=json.loads(path.read_text()) if path.exists() else {'schema_version':'2.3','records':[]}
    payload['records']=[r for r in payload['records'] if r['region_id'] != record['region_id']]+[record]
    write_json(path,payload)
    print(json.dumps({'region_id':record['region_id'],'validated':record['resolution_validated'],'support':record['measurement_support']},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site',choices=['phoenix','jezero','arcadia','marius'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();run(args.site,args.root)
