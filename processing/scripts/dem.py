"""Local GDAL-readable DEM -> centered LAEA analysis window. No downloads."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import math

import numpy as np
from pyproj import CRS
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

from .metrics import METHOD, TOPOGRAPHIC, terrain_features

RADII = {'earth': 6371008.8, 'mars': 3396190.0, 'moon': 1737400.0}
PRODUCTS = {'copernicus': 'earth', 'mola': 'mars', 'lola': 'moon'}


@dataclass(frozen=True)
class DemRequest:
    path: str
    region_id: str
    name: str
    body: str
    product: str
    lat: float
    lon: float
    scale: str
    source_resolution_m: float
    vertical_unit: str
    vertical_reference: str
    source_url: str
    dem_version: str
    accessed_on: str
    analysis_resolution_m: float | None = None
    synthetic: bool = False
    quantity: str = 'elevation'
    georeferencing_verified: bool = False
    source_quality_verified: bool = False
    counts_path: str | None = None
    quality_notes: tuple[str, ...] = ()


def process_dem(request: DemRequest):
    """Return (v2.3 record, meter array). Pair validation is a separate step."""
    r = request
    if PRODUCTS.get(r.product) != r.body:
        raise ValueError('Product/body mismatch')
    if r.scale not in ('local', 'regional'):
        raise ValueError('Unknown scale')
    if not (-90 <= r.lat <= 90 and -180 <= r.lon <= 180):
        raise ValueError('Center must use east-positive longitude in [-180, 180]')
    if r.quantity != 'elevation':
        raise ValueError('Radius, areoid and observation-count products are not elevation DEMs')
    if r.vertical_unit not in ('m', 'km') or not r.vertical_reference.strip():
        raise ValueError('Explicit m/km vertical unit and vertical reference are required')
    if not all((r.source_url, r.dem_version, r.accessed_on, r.region_id)):
        raise ValueError('Source URL, version, access date and region ID are required')
    if Path(r.region_id).name != r.region_id or r.region_id in ('.', '..'):
        raise ValueError('region_id must be a safe filename')
    if not math.isfinite(r.source_resolution_m) or r.source_resolution_m <= 0:
        raise ValueError('source_resolution_m must be positive finite meters')
    spacing = r.analysis_resolution_m if r.analysis_resolution_m is not None else (500 if r.scale == 'local' else 1000)
    window = 10 if r.scale == 'local' else 50
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError('Resolution must be positive finite meters')
    size_float = window * 1000 / spacing
    if not math.isclose(size_float, round(size_float)):
        raise ValueError('Resolution must exactly divide the physical window')
    size = round(size_float)
    if size < 3 or size > 4096:
        raise ValueError('Analysis grid must have 3..4096 cells per side')
    transform = from_origin(-window * 500, window * 500, spacing, spacing)
    path = Path(r.path).expanduser().resolve(strict=True)
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError('Source CRS is missing; provide a correctly labeled DEM')
        crs = CRS.from_wkt(src.crs.to_wkt())
        ellipsoid = crs.ellipsoid
        a, b = ellipsoid.semi_major_metre, ellipsoid.semi_minor_metre
        if not math.isfinite(a) or abs(a / RADII[r.body] - 1) > 0.01:
            raise ValueError('Source CRS radius does not match requested body')
        if not crs.is_geographic and not crs.is_projected:
            raise ValueError('A geographic or projected horizontal CRS is required')
        if src.count != 1 or src.transform.b != 0 or src.transform.d != 0:
            raise ValueError('A single-band north-up DEM is required')
        if src.transform.a <= 0 or src.transform.e >= 0:
            raise ValueError('Unsupported pixel orientation')
        if crs.is_geographic:
            # Conservative upper bound on geographic pixel spacing (equator).
            detected = max(abs(src.transform.a), abs(src.transform.e)) * math.pi / 180 * a
        else:
            factor = crs.axis_info[0].unit_conversion_factor
            detected = max(abs(src.transform.a), abs(src.transform.e)) * factor
        source_resolution = max(detected, r.source_resolution_m)
        if spacing + 1e-6 < source_resolution:
            raise ValueError(f'Upsampling refused: requested {spacing} m, source >= {source_resolution:.3f} m')
        # Retain the source spheroid: no cross-body or datum substitution.
        dst_crs = CRS.from_proj4(f'+proj=laea +lat_0={r.lat} +lon_0={r.lon} '
                                f'+a={a} +b={b} +units=m +no_defs')
        unit = src.units[0]
        if unit and unit.lower() not in ({'m', 'meter', 'metre', 'meters', 'metres'}
                                        if r.vertical_unit == 'm' else {'km', 'kilometer', 'kilometre'}):
            raise ValueError('Declared vertical unit conflicts with raster metadata')
        band_scale, band_offset = src.scales[0], src.offsets[0]
        if r.product == 'lola' and math.isclose(band_offset, a, rel_tol=1e-6):
            raise ValueError('LOLA band offset encodes planetary radius; convert to sphere-relative height first')
        if not all(math.isfinite(v) for v in (band_scale, band_offset)) or band_scale <= 0:
            raise ValueError('Invalid band scale/offset')
        with WarpedVRT(src, crs=dst_crs.to_wkt(), transform=transform,
                       width=size, height=size, dtype='float64', nodata=np.nan,
                       resampling=Resampling.average) as vrt:
            array = vrt.read(1, masked=True).filled(np.nan)
        array = (array * band_scale + band_offset) * (1000 if r.vertical_unit == 'km' else 1)
        array[~np.isfinite(array)] = np.nan
        source_crs = src.crs.to_wkt()
    ratio = float(1 - np.isfinite(array).mean())
    features = terrain_features(array, spacing, False, 'mock' if r.synthetic else 'derived')
    warnings = list(r.quality_notes)
    if ratio > 0:
        warnings.append('Analysis window contains NoData; affected metric neighborhoods are excluded.')
    product_verified = r.synthetic or (r.georeferencing_verified and r.source_quality_verified)
    if not product_verified:
        warnings.append('Product georeferencing and sampling/quality review is not yet verified.')
    eligible = product_verified and ratio <= 0.05 and all(features[k]['value'] is not None for k in TOPOGRAPHIC)
    if not eligible:
        warnings.append('Resolution/quality validation failed: product review incomplete, >5% NoData or missing terrain metric.')
    warnings.append('Awaiting matching target/Earth window, resolution and method validation.')
    with path.open('rb') as source_file:
        source_sha256 = hashlib.file_digest(source_file, 'sha256').hexdigest()
    record = {'schema_version': '2.3', 'region_id': r.region_id,
              'kind': 'candidate' if r.body == 'earth' else 'target',
              'body': r.body, 'name': r.name, 'lat': r.lat, 'lon': r.lon,
              'scale': r.scale, 'window_km': window, 'analysis_resolution_m': spacing,
              'source_resolution_m': source_resolution, 'resolution_validated': False,
              'crs': dst_crs.to_wkt(), 'dem_source': r.product, 'dem_version': r.dem_version,
              'features': features, 'earth_filters': None,
              'quality': {'nodata_ratio': ratio, 'coverage': 'none' if ratio == 1 else
                          ('full' if ratio == 0 else 'partial'), 'warnings': warnings,
                          'validation_eligible': eligible},
              'processing_version': '0.3.0', 'method': METHOD,
              'data_status': 'mock' if r.synthetic else 'derived', 'synthetic': r.synthetic,
              'tags': [], 'provenance': {
                  'source_url': r.source_url, 'accessed_on': r.accessed_on,
                  'source_file': path.name, 'source_file_sha256': source_sha256, 'source_crs': source_crs,
                  'source_radius_m': a, 'vertical_reference': r.vertical_reference,
                  'vertical_unit': r.vertical_unit, 'band_scale': band_scale,
                  'band_offset': band_offset, 'resampling': 'average',
                  'georeferencing_verified': r.georeferencing_verified,
                  'source_quality_verified': r.source_quality_verified,
                  'max_nodata_ratio': 0.05}}
    if r.counts_path is not None:
        with rasterio.open(r.counts_path) as counts:
            if counts.crs is None or counts.crs.to_wkt() != source_crs:
                raise ValueError('Counts CRS does not match elevation source')
            # Counts zero means no direct observation, not missing raster coverage.
            # Materialize only the already-cropped counts raster; never a global map.
            if counts.width * counts.height > 1_000_000:
                raise ValueError('Provide a cropped counts raster (<=1 million pixels)')
            counts_data = counts.read(1, masked=True)
            observed = np.where(np.ma.getmaskarray(counts_data), np.nan,
                                (counts_data.data > 0).astype('float32'))
            from rasterio.warp import reproject
            support = np.full(array.shape, np.nan, dtype='float32')
            reproject(observed, support, src_transform=counts.transform, src_crs=counts.crs, src_nodata=np.nan,
                      dst_transform=transform, dst_crs=dst_crs.to_wkt(), dst_nodata=np.nan,
                      resampling=Resampling.average)
        record['quality']['sampling'] = {
            'counts_file': Path(r.counts_path).name,
            'mean_observed_bin_fraction': float(np.nanmean(support)) if np.isfinite(support).any() else None,
            'min_observed_bin_fraction': float(np.nanmin(support)) if np.isfinite(support).any() else None,
            'analysis_cells_without_counts_coverage': int(np.sum(~np.isfinite(support))),
            'analysis_cells_without_observed_bins': int(np.sum(support == 0)),
            'analysis_cells_total': int(support.size),
            'note': 'Counts > 0 indicate measured source bins; other DEM bins are interpolated. '
                    'This diagnostic does not automatically validate effective resolution.'}
        if not np.isfinite(support).all() or np.any(support == 0):
            record['quality']['validation_eligible'] = False
            record['quality']['warnings'].append(
                'Some analysis cells have no directly observed source bins or no counts coverage.')
    return record, array


def validate_comparison(records):
    """Enable terrain comparison only when an eligible cross-body counterpart exists."""
    for record in records:
        eligible = record['quality']['validation_eligible']
        matched = any(other is not record and other['quality']['validation_eligible']
                      and (other['body'] == 'earth') != (record['body'] == 'earth')
                      and other['synthetic'] == record['synthetic']
                      and all(other[k] == record[k] for k in
                              ('scale', 'window_km', 'analysis_resolution_m', 'method'))
                      for other in records)
        validated = bool(eligible and matched)
        record['resolution_validated'] = validated
        for name in TOPOGRAPHIC:
            f = record['features'][name]
            f['comparable'] = validated and f['value'] is not None
        waiting = 'Awaiting matching target/Earth window, resolution and method validation.'
        record['quality']['warnings'] = [w for w in record['quality']['warnings'] if w != waiting]
        if not validated:
            record['quality']['warnings'].append(waiting)
