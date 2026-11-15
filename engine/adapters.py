"""Convert legacy fixtures, v2.3 JSON and flattened Parquet rows to Region."""
from __future__ import annotations
import math
import pandas as pd
from .models import Region, Feature

ALIASES = {'slope_deg': 'slope_median_deg', 'tri_m': 'tri_median_m'}
TOPO = {'slope_median_deg','slope_p90_deg','flat_fraction','tri_median_m','relief_m','elevation_std_m'}
META = {'schema_version','region_id','id','analog_id','analog_for','theme','source','kind','body','planet','name','lat','lon','scale','window_km','analysis_resolution_m','source_resolution_m','resolution_validated','dem_source','dem_version','features','earth_filters','quality','processing_version','tags','data_status','isSynthetic','method','features_interpolated','measurement_support','method_sensitive'}

def adapt(raw: dict, kind: str | None = None, defaults: list[str] | None = None, configured: set[str] | None = None, warnings: list[str] | None = None) -> Region:
    defaults = defaults if defaults is not None else []
    warnings = warnings if warnings is not None else []
    rid = str(raw.get('region_id') or raw.get('id') or raw.get('analog_id') or '<unknown>')
    legacy = 'isSynthetic' in raw or 'planet' in raw
    status = 'mock' if raw.get('isSynthetic') or raw.get('data_status') == 'synthetic' else raw.get('data_status', 'derived')
    if legacy:
        defaults.append(f'{rid}: legacy synthetic status -> mock')
    resolution = raw.get('resolution_validated')
    if resolution is None:
        resolution = True if legacy else False
        defaults.append(f'{rid}: resolution_validated -> {resolution}')
    scale = raw.get('scale', 'local')
    if 'scale' not in raw: defaults.append(f'{rid}: scale -> local')
    raw_features = raw.get('features')
    if raw_features is None:
        raw_features = {k: v for k,v in raw.items() if k not in META and '__' not in k and (configured is None or k in configured)}
    features = {}
    for old, item in raw_features.items():
        key = ALIASES.get(old, old)
        if configured is not None and key not in configured:
            warnings.append(f'{rid}: unknown feature {old} ignored')
            continue
        if not isinstance(item, dict): item = {'value': item}
        value = item.get('value')
        if value is not None and pd.isna(value): value = None
        if value is not None and (isinstance(value, bool) or not math.isfinite(float(value))):
            raise ValueError(f'{rid}: features.{key}.value invalid')
        fs = item.get('data_status', raw.get(old + '__status', status))
        if fs == 'synthetic': fs = 'mock'
        if 'data_status' not in item and old + '__status' not in raw: defaults.append(f'{rid}: features.{key}.data_status -> {fs}')
        comparable = item.get('comparable', raw.get(old + '__comparable'))
        if comparable is None:
            comparable = bool(resolution and key in TOPO)
            defaults.append(f'{rid}: features.{key}.comparable -> {comparable}')
        features[key] = Feature(value=value, data_status=fs, comparable=bool(comparable), comparability_note=item.get('comparability_note'), uncertainty=item.get('uncertainty') if isinstance(item.get('uncertainty'),(int,float)) else None)
    filters = dict(raw.get('earth_filters') or {})
    filters.update({k.split('__',1)[1]:v for k,v in raw.items() if k.startswith('earth_filters__')})
    filters={key:(value.get('value') if isinstance(value,dict) else value) for key,value in filters.items()}
    tags=raw.get('tags', raw.get('theme'))
    if hasattr(tags,'tolist'): tags=tags.tolist()
    if tags is None: tags=[]
    normalized_kind=raw.get('kind', kind or 'earth_site')
    if normalized_kind=='candidate' and kind=='earth_site':
        normalized_kind='earth_site'
        defaults.append(f'{rid}: kind candidate -> earth_site')
    return Region(region_id=rid, kind=normalized_kind, body='earth' if raw.get('analog_id') and kind != 'target' else str(raw.get('body') or raw.get('planet') or ('earth' if kind != 'target' else 'mars')).lower(), name=raw.get('name', rid), lat=raw.get('lat'), lon=raw.get('lon'), scale=scale, window_km=raw.get('window_km'), analysis_resolution_m=raw.get('analysis_resolution_m'), source_resolution_m=raw.get('source_resolution_m'), resolution_validated=resolution, dem_source=raw.get('dem_source'), dem_version=raw.get('dem_version'), features=features, earth_filters=filters, quality=raw.get('quality') or {}, tags=tags, analog_for=raw.get('analog_for') or [], source=raw.get('source'), processing_version=raw.get('processing_version'), data_status=status, method=raw.get('method'), features_interpolated=raw.get('features_interpolated') or {}, measurement_support=raw.get('measurement_support') or {}, method_sensitive=bool(raw.get('method_sensitive',False)),place=raw.get('place'))
