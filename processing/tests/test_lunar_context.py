from processing.scripts.lunar_context import lunar_context, PRODUCT


def test_polar_surface_mean_is_not_substituted_by_subsurface_model():
    row = {'region_id': 'moon_shackleton_regional', 'lat': -89.9, 'lon': 0, 'window_km': 50}
    c = lunar_context(row)
    assert all(v['value'] is None and v['reason'] for v in c.values())
    assert '2 cm' in c['surface_temp_mean_c']['reason']
    assert c['psr_fraction']['unit'] == '1'
    assert c['surface_temp_max_c']['product_id'] == PRODUCT


def test_nonpolar_temperatures_are_not_extrapolated_from_polar_product():
    c = lunar_context({'region_id':'moon_marius_hills_regional','lat':14.1,'lon':303.2,'window_km':50})
    assert all(v['value'] is None and v['product_id'] is None for v in c.values())
