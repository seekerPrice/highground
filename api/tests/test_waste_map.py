"""Public map links name only current synthetic contributors, never private locations."""
from datetime import UTC, datetime
from unittest.mock import MagicMock
from api.tests.test_waste import record
from api.waste_store import WasteStore


def public_result(*, generation=2, street='Jalan Example', attributed=True, reset=False):
    store=object.__new__(WasteStore)
    store.synthetic_scope=lambda:[{'shop_id':'shop','is_demo':True,'owner_confirmed_street':street,
        'street_assignment_source':'owner_confirmed_current_shop' if attributed else 'unknown',
        'street_confirmed_at':datetime.now(UTC)}]
    fact=record(scenario_generation=generation).model_dump()
    latest={'report_id':'r1','inventory_id':'inv','episode_id':'episode','waste_status':'available','scenario_generation':generation}
    collections={name:MagicMock() for name in ('demo_scenario','waste_scopes','waste_assessments')}
    collections['demo_scenario'].document.return_value.get.return_value.to_dict.return_value={'generation':generation,'state':'ready'}
    if reset:collections['demo_scenario'].document.return_value.get.return_value.to_dict.side_effect=[{'generation':generation,'state':'ready'},{'generation':generation+1,'state':'ready'}]
    query=collections['waste_scopes'].where.return_value
    query.where.return_value=query
    row=MagicMock();row.to_dict.return_value=latest
    query.limit.return_value.stream.return_value=[row]
    collections['waste_assessments'].document.return_value.get.return_value.to_dict.return_value=fact
    store.collection=lambda name:collections[name]
    return store.public(10.)


def test_current_map_links_contain_only_public_identity_and_confirmed_street():
    result=public_result()
    assert result.status=='available'
    assert result.scenario_generation==2
    assert [link.model_dump() for link in result.map_links]==[{'shop_id':'shop','street':'Jalan Example'}]
    assert result.aggregate.streets[0].est_volume_m3==1.
    assert result.missing_or_unavailable_shops==0
    assert all(f'"{key}":' not in result.model_dump_json() for key in ('telegram','media_id','lat','lng','report_id'))


def test_unconfirmed_streets_and_legacy_generation_cannot_produce_map_links():
    for options in ({'attributed':False},{'generation':None},{'street':'Unassigned'}):
        assert public_result(**options).map_links==()


def test_reset_during_public_projection_discards_known_totals_and_map_links():
    result=public_result(reset=True)
    assert result.status=='unavailable' and result.map_links==()
    assert result.aggregate is None and result.assessed_shops is None
