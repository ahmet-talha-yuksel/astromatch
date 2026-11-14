import pytest

from engine.input_adapter import normalize_record, read_records

def real_record(**changes):
    row={"schema_version":"2.3","region_id":"earth_kula_local","kind":"candidate","body":"earth","scale":"local","resolution_validated":True,"features":{"relief_m":{"value":1,"data_status":"derived","comparable":True}},"earth_filters":{"ndvi_mean":{"value":0.2,"data_status":"derived","comparable":False}}}
    row.update(changes); return row

def test_published_wrapper_maps_candidate_and_scalarizes_filters():
    out=read_records({"schema_version":"2.3","records":[real_record()]})[0]
    assert out["kind"]=="earth_site"
    assert out["earth_filters"]=={"ndvi_mean":0.2}
    assert out["features"]["relief_m"]["value"]==1

def test_adapter_preserves_identity_and_provenance():
    row=real_record(provenance={"source_url":"https://example.test/dem"})
    out=normalize_record(row)
    assert out["region_id"]==row["region_id"] and out["provenance"]==row["provenance"]

@pytest.mark.parametrize("bad", [{"x":1}, {"value":"bad"}])
def test_invalid_nested_filter_is_rejected(bad):
    with pytest.raises(ValueError): normalize_record(real_record(earth_filters={"ndvi_mean":bad}))

def test_mock_records_are_not_promoted():
    out=normalize_record(real_record(data_status="mock"))
    assert out["data_status"]=="mock"

def test_legacy_lists_are_not_reinterpreted():
    row={"id":"legacy","name":"Legacy","isSynthetic":True,"earth_filters":[1,2]}
    assert read_records([row])==[row]
