"""Offline nearest populated-place labels from the bundled GeoNames gazetteer."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _geocoder():
    try:
        import numpy as np
        # reverse_geocoder 1.5.1 still uses the removed NumPy np.float alias.
        if not hasattr(np,'float'): np.float=float
        import reverse_geocoder as rg
        # Never allow its fallback code to download data at runtime.
        if not (Path(rg.__file__).parent/'rg_cities1000.csv').is_file(): return None
        return rg.RGeocoder(mode=1,verbose=False)
    except (ImportError,ValueError,OSError):
        return None


def _distance(lat1,lon1,lat2,lon2):
    a,b,c,d=map(math.radians,(lat1,lon1,lat2,lon2))
    s=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(s)))


def places_for(records):
    """Return a place object or None for each Earth record, in input order."""
    result=[None]*len(records)
    indices=[i for i,r in enumerate(records) if r.body=='earth' and r.lat is not None and r.lon is not None]
    geocoder=_geocoder()
    if geocoder is None or not indices: return result
    try:
        matches=geocoder.query([(float(records[i].lat),float(records[i].lon)) for i in indices])
        for i,match in zip(indices,matches):
            name=match.get('name')
            country=match.get('cc')
            if not name or not country: continue
            result[i]={'name':name,'admin1':match.get('admin1') or None,'country_code':country,
                       'distance_km':round(_distance(float(records[i].lat),float(records[i].lon),
                                                     float(match['lat']),float(match['lon'])),1)}
    except (KeyError,TypeError,ValueError,OSError):
        return [None]*len(records)
    return result


def place_phrase(place):
    if not place: return None
    parts=[place['name'],place.get('admin1'),place['country_code']]
    return f"near {', '.join(part for part in parts if part)} ({place['distance_km']:g} km)"
