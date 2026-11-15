"""Normalize a single MER RVF and its PDS4 label, without inventing a map or sol."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = 'https://pds-geosciences.wustl.edu/mer/mer1-m-eng-6-rmc-ops-v1/mer1rm_0xxx/'
NS = {'p': 'http://pds.nasa.gov/pds4/pds/v1'}


def normalize(rvf, label, *, accessed_on):
    rvf, label = Path(rvf), Path(label)
    document = ET.parse(rvf).getroot()
    metadata = ET.parse(label).getroot()
    mission = document.get('mission')
    if mission not in ('MER1', 'MER2') or document.get('variant') != 'Master_RVF':
        raise ValueError('Expected an explicit MER Master_RVF product')
    lid = metadata.findtext('p:Identification_Area/p:logical_identifier', namespaces=NS)
    filename = metadata.findtext('.//p:File/p:file_name', namespaces=NS)
    if not lid or f'{mission.lower()}_rmc:' not in lid or not filename or filename.lower() != rvf.name.lower():
        raise ValueError('PDS4 label does not identify the supplied rover vector file')
    site = int(document.attrib['index1'])
    priorities = [entry.attrib['solution_id'] for entry in document.findall('priority/entry')]
    if not priorities: raise ValueError('RMC solution priority list is required')
    chosen = {}
    for solution in document.findall('solution'):
        reference, offset, orientation = (solution.find(key) for key in ('reference_frame', 'offset', 'orientation'))
        if (solution.get('name') != 'ROVER_FRAME' or reference is None or reference.get('name') != 'SITE_FRAME'
                or int(reference.get('index1', '-1')) != site or offset is None or orientation is None):
            raise ValueError('A site RVF must reference its own SITE_FRAME')
        rmc = [int(solution.get(f'index{i}', '0')) for i in range(1, 7)]
        if rmc[0] != site or min(rmc) < 0: raise ValueError('Invalid rover motion counter')
        xyz = [float(offset.attrib[key]) for key in ('x', 'y', 'z')]
        quaternion = [float(orientation.attrib[key]) for key in ('s', 'v1', 'v2', 'v3')]
        if not all(math.isfinite(v) for v in (*xyz, *quaternion)) or abs(sum(v*v for v in quaternion)-1) > .01:
            raise ValueError('Nonfinite position or invalid orientation')
        solution_id = solution.attrib['solution_id']
        if solution_id not in priorities: raise ValueError('Unknown solution priority')
        rank = priorities.index(solution_id)
        record = {'rover': 'Opportunity' if mission == 'MER1' else 'Spirit', 'site': site, 'drive': rmc[1],
                  'idd': rmc[2], 'pma': rmc[3], 'hga': rmc[4], 'tweak': rmc[5], 'rmc': rmc,
                  'offset_m': xyz, 'orientation_s_v1_v2_v3': quaternion, 'solution_id': solution_id,
                  'solution_added_at': solution.get('add_date'), 'sol': None, 'observation_utc': None,
                  'latitude': None, 'longitude': None, 'data_status': 'derived'}
        key = tuple(rmc)
        if key not in chosen or rank >= chosen[key][0]: chosen[key] = (rank, record)
    records = [chosen[key][1] for key in sorted(chosen)]
    if not records: raise ValueError('No usable coordinate definitions')
    base = BASE.replace('mer1',mission.lower())
    return {'schema_version': 'mer-local-reference-1', 'mission': mission, 'rover': records[0]['rover'],
            'site': site, 'coordinate_frame': f'SITE_FRAME {site}', 'position_unit': 'm', 'records': records,
            'geographic_registration': None, 'registered_terrain_id': None,
            'limitations': ['Local coordinate definitions, not a geographically registered traverse.',
                           'RMC counts are actuator identifiers, not distances or continuous dynamics telemetry.',
                           'add_date is solution metadata, not observation time; sol remains null.',
                           'Combining sites requires the matching SVF and coordinate transforms.'],
            'provenance': {'product_lid': lid, 'source_url': base+'data/'+rvf.name,
                           'label_url': base+'data/'+label.name, 'specification_url': base+'document/rmc_sis.htm',
                           'coordinate_units_url': 'https://pds-imaging.jpl.nasa.gov/documentation/MER_camsis_v4_9-25-07.pdf',
                           'source_sha256': hashlib.sha256(rvf.read_bytes()).hexdigest(),
                           'label_sha256': hashlib.sha256(label.read_bytes()).hexdigest(),
                           'accessed_on': accessed_on, 'method': 'priority-selected RVF definitions; original offsets/quaternions retained'}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rvf', type=Path); parser.add_argument('label', type=Path)
    parser.add_argument('--accessed-on', required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = normalize(args.rvf, args.label, accessed_on=args.accessed_on)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(f"{output['rover']}: {len(output['records'])} coordinate definitions; {output['coordinate_frame']}; no invented sol or geographic binding")
