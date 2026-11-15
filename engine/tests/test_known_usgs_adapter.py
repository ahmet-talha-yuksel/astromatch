from engine.adapters import adapt
from engine.mock import generate
from engine.models import Dataset
from engine.ranking import rank


def test_usgs_fields_are_preserved_without_mislabeling_the_body():
    analog = adapt({
        'analog_id': 'usgs_0192', 'name': 'Example site', 'lat': 12.5, 'lon': 35.5,
        'theme': ['volcanic_eruption'], 'analog_for': ['mars'],
        'source': 'USGS P9J72921',
    }, kind='earth_site')
    assert analog.region_id == 'usgs_0192'
    assert analog.tags == ['volcanic_eruption']
    assert analog.analog_for == ['mars']
    assert analog.body == 'earth'
    assert analog.source == 'USGS P9J72921'


def test_usgs_proximity_does_not_mark_a_candidate_as_known():
    targets, candidates, _ = generate(n_grid=10)
    candidate = next(row for row in candidates if row['region_id'] == 'S-01' and row['scale'] == 'regional')
    target = adapt(targets[1])
    site = adapt(candidate)
    usgs = adapt({
        'analog_id': 'usgs_0001', 'name': 'Near the candidate',
        'lat': candidate['lat'], 'lon': candidate['lon'],
        'theme': ['impact_crater'], 'analog_for': [], 'source': 'USGS P9J72921',
    }, kind='earth_site')
    ds = Dataset(targets=[target], candidates=[site], known_analogs=[usgs], mode='mock')
    result = rank(ds, target.region_id, 'regional', k=1)
    row = result.top_k[0]
    assert row['distance_to_usgs_site_km'] == 0
    assert 'distance_to_known_km' not in row
    assert row['is_known'] is False
    assert [r['id'] for r in result.novel_candidates] == [site.region_id]

    ds.known_analogs.append(site)
    exact = rank(ds, target.region_id, 'regional', k=1)
    assert exact.top_k[0]['is_known'] is True
    assert exact.novel_candidates == []
    assert exact.top_k[0]['distance_to_usgs_site_km'] == 0
