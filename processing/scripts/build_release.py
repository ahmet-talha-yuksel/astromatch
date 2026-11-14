"""Rebuild the complete current v2.3 delivery from already acquired local inputs."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path

from .apply_srtm_sources import apply
from .assemble_release import assemble
from .enrich_environment import enrich
from .finish_pilot import finish
from .package_handoff import package
from .modis import CMGFile
from .process_dem import run
from .publish_release import publish,publish_grid
from .review_targets import review as review_targets


def build(root, *, lst, ndvi, accessed_on):
    root = Path(root).resolve()
    expanded_acquisition=root/'raw/pilot_expanded/acquisition.json'
    expanded_landmask=root/'raw/worldcover/landmask_expanded.json'
    has_expanded=expanded_acquisition.exists() or expanded_landmask.exists()
    if has_expanded:
        if not expanded_acquisition.exists() or not expanded_landmask.exists():
            raise ValueError('Expanded land-mask acquisition is incomplete; resume expand_pilot first')
        acquired=json.loads(expanded_acquisition.read_text())
        masked=json.loads(expanded_landmask.read_text())
        expected={a['region_id'] for a in acquired['attempts'] if a['status']=='ready'}
        if expected!={r['region_id'] for r in masked['records']}:
            raise ValueError('Expanded land-mask acquisition is incomplete; resume expand_pilot first')
    # Validate both supplied file paths before regenerating any current output.
    for path in (lst, ndvi):
        if not Path(path).is_file():raise FileNotFoundError(path)
    with ExitStack() as stack:
        readers = []
        for product, path in (('MOD11C3', lst), ('MOD13C2', ndvi)):
            reader = CMGFile(path, product, accessed_on)
            stack.callback(reader.close)
            readers.append(reader)
        if readers[0].period != readers[1].period:
            raise ValueError('Release MODIS inputs must have matching monthly periods')
    apply(root)
    config = assemble(root)
    output = root/'out/real'
    run(config, output)
    enrich(output, lst_path=lst, ndvi_path=ndvi, accessed_on=accessed_on)
    review_targets(root,output)
    finish(root)
    publish(output, root/'out')
    if has_expanded:
        comparison=json.loads((output/'features.json').read_text())['records']
        finish(root,acquisition_path=expanded_acquisition,landmask_path=expanded_landmask,
               output=root/'out/pilot_expanded',comparison_records=comparison)
        publish_grid(root/'out/pilot_expanded',root/'out')
    else:
        publish_grid(root/'out/pilot',root/'out')
    return package(output, root/'out/handoff/kisi2_v2_3.zip')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--lst', type=Path, required=True)
    parser.add_argument('--ndvi', type=Path, required=True)
    parser.add_argument('--accessed-on', required=True)
    args = parser.parse_args()
    print(build(args.root, lst=args.lst, ndvi=args.ndvi, accessed_on=args.accessed_on))
