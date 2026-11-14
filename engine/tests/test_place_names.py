from engine.models import Region
from engine.place_names import place_phrase, places_for
from engine import load_dataset,rank


def test_known_turkish_coordinates_and_non_earth():
    rows=[Region(region_id='salda',kind='earth_site',body='earth',name='Salda',lat=37.54,lon=29.67),
          Region(region_id='tuz',kind='earth_site',body='earth',name='Tuz Gölü',lat=38.8,lon=33.56),
          Region(region_id='mars',kind='target',body='mars',name='Mars',lat=37.54,lon=29.67)]
    salda,tuz,mars=places_for(rows)
    assert salda['name']=='Yesilova' and salda['admin1']=='Burdur' and salda['country_code']=='TR'
    assert tuz['name']=='Sereflikochisar' and tuz['country_code']=='TR'
    assert salda['distance_km']>=0 and tuz['distance_km']>=0
    assert 'near Yesilova, Burdur, TR' in place_phrase(salda)
    assert mars is None


def test_lookup_failure_returns_null(monkeypatch):
    monkeypatch.setattr('engine.place_names._geocoder',lambda:None)
    row=Region(region_id='x',kind='earth_grid',body='earth',name='x',lat=0,lon=0)
    assert places_for([row])==[None]


def test_rank_and_explanation_carry_offline_place():
    ds=load_dataset(mock=True,mock_n_grid=10)
    result=rank(ds,'T-01','local')
    assert all(row['place'] is not None for row in result.full_scores)
    assert result.top_k[0]['explanation']['place']==result.top_k[0]['place']
    assert 'near ' in result.top_k[0]['explanation']['summary']
    assert all(target.place is None for target in ds.targets)
