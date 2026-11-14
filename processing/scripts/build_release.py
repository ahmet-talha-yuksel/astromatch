"""Rebuild the complete current v2.3 delivery from already acquired local inputs."""
import argparse
from contextlib import ExitStack
from pathlib import Path

from .apply_srtm_sources import apply
from .assemble_release import assemble
from .enrich_environment import enrich
from .finish_pilot import finish
from .package_handoff import package
from .modis import CMGFile
from .process_dem import run
from .publish_release import publish


def build(root, *, lst, ndvi, accessed_on):
    root = Path(root).resolve()
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
    finish(root)
    publish(output, root/'out')
    return package(output, root/'out/handoff/kisi2_v2_3.zip')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--lst', type=Path, required=True)
    parser.add_argument('--ndvi', type=Path, required=True)
    parser.add_argument('--accessed-on', required=True)
    args = parser.parse_args()
    print(build(args.root, lst=args.lst, ndvi=args.ndvi, accessed_on=args.accessed_on))
