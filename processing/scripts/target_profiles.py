"""Reviewable, non-scoring literature context. Sources opened 2026-11-15."""
from copy import deepcopy
import json
from pathlib import Path

DIMENSIONS = ('water_ice', 'surface_material', 'thermal', 'dust_wind', 'illumination')
EVIDENCE = {'direct_measurement', 'orbital_remote_sensing', 'model', 'literature_synthesis'}
WATER = {'direct_observation', 'orbital_indicator', 'modeled', 'absent', 'unknown', 'not_applicable'}
SOURCES = {
    'phoenix': ('Mars Phoenix', 'https://science.nasa.gov/mission/mars-phoenix/'),
    'arcadia': ('Arcadia Planitia', 'https://science.nasa.gov/resource/arcadia-planitia/'),
    'jezero': ('What a Lake in Turkey Can Tell Us about Mars', 'https://science.nasa.gov/blogs/earth-matters/2021/02/17/what-a-lake-in-turkey-can-tell-us-about-mars/'),
    'marius': ('Marius Hills Pit - Lava Tube Skylight?', 'https://www.lroc.im-ldi.com/images/202'),
    'shackleton': ('NASA Spacecraft Reveals Ice Content in Moon Crater', 'https://www.lpi.usra.edu/features/LRO/072512/'),
    'salda': ('Lake Salda Beach', 'https://www.jpl.nasa.gov/images/pia24375-lake-salda-beach/'),
    'haughton': ('Microbial Preservation in Sulfates in the Haughton Impact Structure Suggests Target in Search for Life on Mars', 'https://ntrs.nasa.gov/search.jsp?R=20050173938'),
    'meteor_crater': ('Barringer Meteor Crater, Arizona', 'https://science.nasa.gov/photojournal/barringer-meteor-crater-arizona/'),
}


def unknown(dimension):
    value = {'category': 'unknown', 'summary': None, 'evidence': None,
             'spatial_scope': None, 'source': None, 'verified_by': None,
             'notes': 'No applicable site-specific claim was verified in this session.'}
    if dimension == 'surface_material': value['minerals'] = []
    if dimension == 'thermal': value['values'] = {'surface_temp_min_c': None, 'surface_temp_max_c': None}
    return value


def claim(category, summary, key, *, evidence='literature_synthesis', scope='site', minerals=None):
    title, url = SOURCES[key]
    result = {'category': category, 'summary': summary, 'evidence': evidence,
              'spatial_scope': scope, 'source': {'title': title, 'url_or_doi': url,
              'accessed_on': '2026-11-15'}, 'verified_by': None,
              'notes': 'Literature context only; not a DEM-window measurement or scoring feature.'}
    if minerals is not None: result['minerals'] = minerals
    return result


def profiles(earth_ids):
    targets = []
    for tid, rid in [('T-01','mars_jezero_regional'), ('T-02','moon_shackleton_regional'),
                     ('T-03','moon_marius_hills_regional'), ('T-04','mars_phoenix_regional'),
                     ('T-05','mars_arcadia_regional')]:
        dims = {d: unknown(d) for d in DIMENSIONS}
        targets.append({'target_id': tid, 'region_id': rid, 'dimensions': dims})
    j, s, m, p, a = [r['dimensions'] for r in targets]
    j['surface_material'] = claim('carbonate_bearing_paleolake',
        'Orbital observations indicate possible carbonate along the former western lake margin of Jezero.',
        'jezero', evidence='orbital_remote_sensing', scope='regional', minerals=['carbonate'])
    s['water_ice'] = claim('orbital_indicator',
        'Laser reflectance measurements of the Shackleton floor are consistent with small amounts of ice; not a direct ice detection.',
        'shackleton', evidence='orbital_remote_sensing')
    s['illumination'] = claim('permanently_shadowed_interior',
        'The crater interior is permanently dark while parts of the upper walls receive sunlight.', 'shackleton')
    m['surface_material'] = claim('volcanic_pit',
        'The Marius Hills pit lies within a sinuous rille and is interpreted as a possible collapsed lava-tube roof.',
        'marius', evidence='orbital_remote_sensing', minerals=[])
    p['water_ice'] = claim('direct_observation',
        'Phoenix analyzed a collected sample and confirmed subsurface water ice at its landing site.',
        'phoenix', evidence='direct_measurement')
    p['surface_material'] = claim('perchlorate_bearing_soil',
        'Phoenix detected perchlorate in soil at its landing site.', 'phoenix', evidence='direct_measurement', minerals=['perchlorate'])
    a['water_ice'] = claim('orbital_indicator',
        'Rounded ridges in the cited Arcadia THEMIS image suggest ground ice; this is a regional geomorphic interpretation.',
        'arcadia', evidence='orbital_remote_sensing', scope='regional')
    for dims in (s, m):
        dims['dust_wind'] = {'category':'not_applicable','summary':None,'evidence':None,
                             'spatial_scope':None,'source':None,'verified_by':None,
                             'notes':'Atmospheric dust/wind dimension is not applicable to this lunar profile.'}
    earth = []
    for rid in earth_ids:
        dims = {d: unknown(d) for d in DIMENSIONS}
        if rid.startswith('earth_salda_'):
            dims['surface_material'] = claim('carbonate_lake_deposits',
                'White sands and rocks on the eastern Salda shore are carbonate precipitates from the lake.',
                'salda', minerals=['carbonate'])
        elif rid.startswith('earth_haughton_'):
            dims['surface_material'] = claim('impact_hydrothermal_deposits',
                'Haughton impact deposits include gypsum-bearing carbonates and remobilized sulfates.',
                'haughton', minerals=['gypsum','carbonate'])
        elif rid.startswith('earth_meteor_crater_'):
            dims['surface_material'] = claim('impact_sandstone_terrain',
                'Barringer Crater cuts desert sandstone west of Winslow, Arizona.', 'meteor_crater', minerals=[])
        earth.append({'region_id':rid,'dimensions':dims})
    result = {'schema_version':'profile-1.0','targets':targets,'earth_sites':earth}
    validate_profiles(result)
    return result


def validate_profiles(doc):
    if doc['schema_version'] != 'profile-1.0': raise ValueError('Unknown profile schema')
    ids = [r['region_id'] for r in doc['targets']+doc['earth_sites']]
    if len(ids) != len(set(ids)): raise ValueError('Duplicate region_id')
    for row in doc['targets']+doc['earth_sites']:
        if set(row['dimensions']) != set(DIMENSIONS): raise ValueError('Missing dimensions')
        for name, item in row['dimensions'].items():
            if item.get('verified_by') is not None: raise ValueError('Human verification is pending')
            category = item.get('category')
            if name == 'water_ice' and category not in WATER: raise ValueError('Invalid water_ice category')
            if item.get('evidence') is not None and item['evidence'] not in EVIDENCE: raise ValueError('Invalid evidence')
            if item.get('spatial_scope') not in (None,'site','regional','global'): raise ValueError('Invalid spatial scope')
            numeric = any(v is not None for v in item.get('values',{}).values())
            nonnull = bool(item.get('summary') or numeric or item.get('minerals') or category not in ('unknown','not_applicable',None))
            if nonnull and not (item.get('source',{}).get('title') and item.get('source',{}).get('url_or_doi') and item.get('evidence')):
                raise ValueError('Non-null claims require source and evidence')
            if category in ('unknown','not_applicable') and (item.get('source') is not None or item.get('evidence') is not None):
                raise ValueError('Unknown/not-applicable has no asserted evidence/source')


def build(root=Path('processing')):
    path = root/'out/real'
    earth_ids = [r['region_id'] for r in json.loads((path/'features.json').read_text(encoding='utf-8'))['records'] if r.get('body')=='earth']
    doc = profiles(earth_ids)
    (path/'target_profiles.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    lines = ['# Profile review queue','', 'All sources below were opened 2026-11-15. All verified_by fields remain null.',
             'Claims are site/regional literature context, not integrated DEM-window measurements. No literature temperature replaces a missing Diviner statistic.',
             'Unknown dimensions are intentional gaps; no source was verified for that dimension in this session.',
             '', '| Record | Dimension | Claim / gap | Source |','|---|---|---|---|']
    count = 0
    for r in doc['targets']+doc['earth_sites']:
        for dim,item in r['dimensions'].items():
            link = item['source']['url_or_doi'] if item.get('source') else 'null'
            content = item.get('summary') or f'{item["category"]}: {item["notes"]}'
            lines.append(f'| {r["region_id"]} | {dim} | {content} | {link} |')
            count += bool(item.get('summary'))
    (path/'PROFILE_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'targets':len(doc['targets']),'earth_site_records':len(doc['earth_sites']),'sourced_dimension_records':count}


if __name__ == '__main__':
    print(json.dumps(build(),indent=2))
