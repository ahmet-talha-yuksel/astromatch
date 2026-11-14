"""Read bounded HDF4 CMG windows with product-specific MOD11C3/MOD13C2 QA.

Official specifications:
https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11C3
https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13C2
No authentication or downloads are performed here.
"""
from datetime import datetime, timedelta
import hashlib
import math
from pathlib import Path
import re

import numpy as np
from pyhdf.SD import SD, SDC
from pyproj import CRS, Transformer

from .acquire_earth_sites import footprint_bounds
from .metrics import feature

STEP = .05
SHAPE = (3600, 7200)
NDVI = 'CMG 0.05 Deg Monthly NDVI'
NDVI_QA = 'CMG 0.05 Deg Monthly VI Quality'
RELIABILITY = 'CMG 0.05 Deg Monthly pixel reliability'


def lst_qa(qc):
    qc = np.asarray(qc, dtype=np.uint8)
    # MOD11C3 bit 2 is data quality; bit 3 is combined Terra/Aqua use.
    return ((qc & 3) == 0) & (((qc >> 2) & 1) == 0) & (((qc >> 6) & 3) == 0)


def ndvi_qa(qc, reliability):
    qc = np.asarray(qc, dtype=np.uint16)
    return ((qc & 3) == 0) & (((qc >> 2) & 15) <= 2) & (((qc >> 6) & 3) != 3) & (
        (qc & ((1 << 8) | (1 << 10))) == 0) & (((qc >> 11) & 7) == 1) & (
        ((qc >> 14) & 3) >= 2) & (np.asarray(reliability) == 0)


def calibrated(raw, attrs, product):
    raw = np.asarray(raw)
    low, high = attrs['valid_range']
    valid = (raw >= low) & (raw <= high) & (raw != attrs['_FillValue'])
    scale, offset = float(attrs['scale_factor']), float(attrs.get('add_offset', 0))
    if not math.isfinite(scale) or scale <= 0 or not math.isfinite(offset):
        raise ValueError('Invalid MODIS calibration')
    if product == 'MOD11C3':
        if not np.isclose(scale, .02) or offset != 0 or attrs.get('units') != 'K':
            raise ValueError('Unexpected MOD11C3 temperature encoding')
        values = raw.astype(float) * scale - 273.15
    elif product == 'MOD13C2':
        # CMG VI metadata uses a DIVISOR (10000), unlike MOD11's multiplier.
        if not np.isclose(scale, 10000) or offset != 0:
            raise ValueError('Unexpected MOD13C2 NDVI encoding')
        values = (raw.astype(float) - offset) / scale
    else:
        raise ValueError('Unsupported MODIS product')
    return np.where(valid, values, np.nan)


def weighted_mean(values, weights):
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    return float(np.average(values[valid], weights=weights[valid])) if valid.any() else None


def circular_hour(values, weights):
    valid = np.isfinite(values) & (weights > 0)
    if not valid.any():
        return None
    angles = values[valid] * np.pi / 12
    z = np.average(np.exp(1j * angles), weights=weights[valid])
    if abs(z) < 1e-8:
        return None
    return float((np.angle(z) * 12 / np.pi) % 24)


def cmg_window(record):
    """CMG center sampling inside the actual 10/50 km LAEA physical window."""
    width = record['window_km'] * 1000
    if record['body'] != 'earth' or width not in (10000, 50000):
        raise ValueError('MODIS windows require Earth and a v2.3 physical scale')
    west, south, east, north = footprint_bounds(record['lat'], record['lon'], width)
    if west < -180 or east > 180:
        raise ValueError('CMG dateline crossing requires a split window')
    row0, row1 = max(0, math.floor((90-north)/STEP)), min(3600, math.ceil((90-south)/STEP))
    col0, col1 = max(0, math.floor((west+180)/STEP)), min(7200, math.ceil((east+180)/STEP))
    lon, lat = np.meshgrid(-180+(np.arange(col0, col1)+.5)*STEP,
                           90-(np.arange(row0, row1)+.5)*STEP)
    crs = CRS.from_proj4(f'+proj=laea +lat_0={record["lat"]} +lon_0={record["lon"]} +datum=WGS84 +units=m')
    x, y = Transformer.from_crs('EPSG:4326', crs, always_xy=True).transform(lon, lat)
    inside = (np.abs(x) <= width/2) & (np.abs(y) <= width/2)
    weights = np.where(inside, np.cos(np.radians(lat)), 0.)
    return (row0, col0), (row1-row0, col1-col0), weights


class CMGFile:
    def __init__(self, path, product, accessed_on):
        self.path, self.product = Path(path), product
        match = re.fullmatch(r'(MOD11C3|MOD13C2)\.A(\d{7})\.061\.\d{13}\.hdf', self.path.name)
        if not match or match[1] != product:
            raise ValueError('Expected named MOD11C3/MOD13C2 collection 061 HDF granule')
        start = datetime.strptime(match[2], '%Y%j')
        if start.day != 1 or start.strftime('%Y%j') != match[2]:
            raise ValueError('Monthly CMG granule must begin on the first day')
        following = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        self.period = {'start': start.date().isoformat(),
                       'end': (following-timedelta(days=1)).date().isoformat()}
        datetime.strptime(accessed_on, '%Y-%m-%d')
        self.handle = SD(str(self.path), SDC.READ)
        try:
            attrs = self.handle.attributes()
            expected = f'10.5067/MODIS/{product}.061'
            if attrs.get('identifier_product_doi', '').strip('\x00') != expected:
                raise ValueError('HDF DOI does not match named collection/product')
            structure = re.sub(r'\s', '', attrs.get('StructMetadata.0', ''))
            for required in ('XDim=7200', 'YDim=3600', 'Projection=GCTP_GEO',
                             'UpperLeftPointMtrs=(-180000000.000000,90000000.000000)',
                             'LowerRightMtrs=(180000000.000000,-90000000.000000)'):
                if required not in structure:
                    raise ValueError('Unexpected CMG grid/georeferencing metadata')
            if 'GridOrigin=' in structure and 'GridOrigin=HDFE_GD_UL' not in structure:
                raise ValueError('Expected upper-left CMG origin')
            if 'PixelRegistration=' in structure and 'PixelRegistration=HDFE_CENTER' not in structure:
                raise ValueError('Expected center-registered CMG pixels')
            if self.path.name not in attrs.get('CoreMetadata.0', ''):
                raise ValueError('HDF local granule identity mismatch')
            with self.path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            self.provenance = {'product': product+'.061', 'file': self.path.name,
                               'file_sha256': digest, 'bytes': self.path.stat().st_size,
                               'doi': expected, 'source_url': 'https://doi.org/'+expected,
                               'specification_url': f'https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/{product}',
                               'accessed_on': accessed_on, 'period': self.period,
                               'native_grid_step_deg': STEP, 'crs': 'EPSG:4326',
                               'grid_origin': 'HDFE_GD_UL (HDF-EOS default when omitted)',
                               'spatial_method': 'CMG center sampling within physical LAEA window; cosine-latitude area weights; no downscaling'}
        except Exception:
            self.handle.end()
            raise

    def close(self):
        self.handle.end()

    def read(self, name, start, count):
        sds = self.handle.select(name)
        try:
            if tuple(sds.info()[2]) != SHAPE:
                raise ValueError('Unexpected CMG dataset dimensions')
            return np.asarray(sds.get(start=start, count=count)), sds.attributes()
        finally:
            sds.endaccess()

    def extract(self, record):
        start, count, weights = cmg_window(record)
        quality = {'selected_cmg_pixels': int((weights > 0).sum()), 'period': self.period}
        result = {'features': {}, 'earth_filters': {}, 'quality': quality}
        if self.product == 'MOD13C2':
            raw, attrs = self.read(NDVI, start, count)
            qc, qa_attrs = self.read(NDVI_QA, start, count)
            legend = re.sub(r'\s', '', qa_attrs.get('Legend', ''))
            if not all(key in legend for key in ('[11-13]', '[14-15]', '001:Land')):
                raise ValueError('Unexpected MOD13C2 collection 061 QA legend')
            reliability, _ = self.read(RELIABILITY, start, count)
            values = np.where(ndvi_qa(qc, reliability), calibrated(raw, attrs, self.product), np.nan)
            value = weighted_mean(values, weights)
            result['earth_filters']['ndvi_mean'] = {**feature(value, status='derived'),
                'filter_note': 'Monthly quality-filtered land NDVI; auxiliary filter only, never a similarity score.'}
            quality['ndvi'] = self.quality(values, weights)
            quality['qa_policy'] = 'MOD13C2.061 file Legend: mandatory=0, usefulness<=2, aerosol!=high, no adjacent/mixed clouds, land bits11:13=001, geospatial bits14:15>=2, reliability=0; historical fills excluded.'
            quality['qa_legend_source'] = 'Actual HDF SDS Legend attribute. Older LAADS file-spec land/water bit layout is not applied to this collection 061 file.'
        else:
            data = {}
            for phase in ('Day', 'Night'):
                raw, attrs = self.read('LST_'+phase+'_CMG', start, count)
                qc, _ = self.read('QC_'+phase, start, count)
                values = np.where(lst_qa(qc), calibrated(raw, attrs, self.product), np.nan)
                data[phase] = values
                quality[phase.lower()] = self.quality(values, weights)
                time, time_attrs = self.read(phase+'_view_time', start, count)
                low, high = time_attrs['valid_range']
                valid = (time != time_attrs['_FillValue']) & (time >= low) & (time <= high) & np.isfinite(values)
                hours = np.where(valid, time.astype(float)*float(time_attrs['scale_factor']), np.nan)
                quality[phase.lower()]['mean_view_hour_utc'] = circular_hour(hours, weights)
                name = 'surface_temp_monthly_'+phase.lower()+'_c'
                result['features'][name] = {**feature(weighted_mean(values, weights), status='derived'),
                    'comparability_note': 'Monthly Terra clear-sky overpass LST; no matched cross-body temperature protocol.'}
            difference = data['Day']-data['Night']  # Same spatial support, not difference of disjoint means.
            result['features']['surface_temp_monthly_overpass_difference_c'] = {
                **feature(weighted_mean(difference, weights), status='derived'),
                'comparability_note': 'Difference of monthly day/night overpass LST on paired valid CMG pixels. Not daily Tmax-minus-Tmin amplitude.'}
            quality['paired_day_night'] = self.quality(difference, weights)
            quality['qa_policy'] = 'MOD11C3-CMG: mandatory bits0:1=0, L1B-quality bit2=0, average LST error bits6:7=0; combined-use bit3 is not a quality failure.'
            quality['uncertainty'] = {'kind': 'source_QC_category', 'average_lst_error_category_upper_k': 1,
                                      'note': 'Product QA category, not an independent error bound or confidence interval for this window.'}
            quality['temperature_protocol'] = {'status': 'unmatched', 'comparable': False,
                                               'note': 'No Diviner/MEDA pair with the same statistic and comparable local-time/season coverage.'}
        return result

    @staticmethod
    def quality(values, weights):
        accepted = np.isfinite(values) & (weights > 0)
        total = float(weights.sum())
        fraction = float(np.clip(weights[accepted].sum()/total, 0, 1)) if total > 0 else 0.
        return {'accepted_pixels': int(accepted.sum()),
                'accepted_area_fraction': fraction,
                'coverage_note': 'Mean represents accepted CMG pixels only; less than half of sampled window area passes QA.' if 0 < fraction < .5 else None,
                'missing_reason': None if accepted.any() else 'No quality-accepted CMG centers in the physical window.'}
