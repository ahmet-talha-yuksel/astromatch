"""Document Diviner product semantics; never substitute subsurface/model for surface observations."""
import json
from pathlib import Path

LABEL = 'https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/dlre_prp_south.xml'
PRODUCT = 'urn:nasa:pds:lro_diviner_derived1:data_derived_prp:dlre_prp_south::1.0'


def lunar_context(record):
    polar = record['region_id'].startswith(('moon_shackleton_', 'moon_mons_mouton_'))
    reasons = {
        'surface_temp_max_c': 'PRP temp_max is a calculated annual surface maximum; not ingested as an orbital measured window statistic. No validated triangle-area/LAEA extraction.',
        'surface_temp_min_c': 'PRP has no minimum surface-temperature field; no validated alternative product extraction.',
        'surface_temp_mean_c': 'PRP temp_avg is calculated at 2 cm depth, not mean surface temperature; incompatible statistic.',
        'psr_fraction': 'PRP ice_depth is not a permanent-shadow mask; no validated PSR product/window extraction.',
    }
    return {name: {'value': None, 'unit': '1' if name == 'psr_fraction' else 'degC',
                   'source': 'LRO Diviner PRP' if polar else 'LRO Diviner global product not selected',
                   'product_id': PRODUCT if polar else None, 'source_url': LABEL if polar else None,
                   'version': '1.0' if polar else None, 'source_resolution_m': None,
                   'evidence': 'orbital_remote_sensing', 'window_km': record['window_km'],
                   'lat': record['lat'], 'lon': record['lon'], 'lunar_radius_m': 1737400,
                   'method': 'No raster/triangle values extracted; no literature temperatures substituted.',
                   'reason': reason if polar else 'nonpolar_global_product_not_validated; no reliable temperature extraction'}
            for name, reason in reasons.items()}


def build(root=Path('processing')):
    path = root/'out/real/features.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    rows = [r for r in payload['records'] if r.get('body') == 'moon' and
            r['region_id'].startswith(('moon_shackleton_', 'moon_marius_hills_', 'moon_mons_mouton_'))]
    for row in rows:
        row['context'] = {**row.get('context', {}), **lunar_context(row)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    report = root/'out/real/context_report.md'
    with report.open('a', encoding='utf-8') as stream:
        stream.write('\n## Diviner thermal context\n\n')
        stream.write('Metadata opened 2026-11-15: '+LABEL+' (HTTP 200).\n\n')
        stream.write('Product '+PRODUCT+'; lunar reference radius 1737.4 km. Mesh resolution is not a uniform raster pixel size and was not established.\n')
        stream.write('The PRP table contains modeled annual surface maxima, modeled annual average at 2 cm depth and ice stability depth. It supplies neither the requested mean/minimum surface observation nor a PSR mask. No derived values are mislabeled as direct orbital surface measurements.\n\n')
        for row in rows:
            for name, item in row['context'].items():
                stream.write(f'- {row["region_id"]} / {name}: null; {item["reason"]}\n')
    return len(rows)


if __name__ == '__main__':
    print('Moon targets with explicit missing thermal context:', build())
