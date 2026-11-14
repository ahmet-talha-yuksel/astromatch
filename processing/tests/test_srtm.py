import zipfile

import pytest

from processing.scripts.import_srtm import tile_geometry, import_archive
from processing.scripts.apply_srtm_sources import choose_tile


@pytest.mark.parametrize('name,expected', [
    ('e020n90', (20, 90, 6000, 4800)),
    ('e020n40', (20, 40, 6000, 4800)),
    ('w100s10', (-100, -10, 6000, 4800)),
])
def test_srtm_tiles_have_fifty_degree_latitude_extent(name, expected):
    assert tile_geometry(name) == expected


def test_import_rejects_truncated_archive_before_writing(tmp_path):
    archive=tmp_path/'e020n40.SRTMGL30.dem.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('E020N40.DEM', b'\0\0')
    target=tmp_path/'invalid.tif'
    with pytest.raises(ValueError, match='layout/size'):
        import_archive(archive, target)
    assert not target.exists()


def test_srtm_tile_selection_excludes_gtopo_latitudes_and_seams():
    entries=[{'bounds':[20,-10,60,40]}, {'bounds':[20,40,60,90]}]
    assert choose_tile(30,38,entries)==entries[0]
    assert choose_tile(30,45,entries)==entries[1]
    assert choose_tile(30,75,entries) is None
    assert choose_tile(30,40,entries) is None  # Physical window spans two files.
