import asyncio
import json
from pathlib import Path
from unittest.mock import patch
import httpx
from api.config import Settings
from api.public_check import PublicCheckReader,create_public_check_reader,fixed_check_danger,location_routing
from api.tests.test_public_check import NOW,LOCATION,source,warning,project_check

class Snapshot:
    def __init__(self,identity,value):self.id,self.value=identity,value
    def to_dict(self):return self.value
class Collection:
    def __init__(self,rows):self.rows,self.bound=rows,None
    def where(self,**kwargs):
        query=kwargs['filter']
        if query.op_string=='==':self.rows=[row for row in self.rows if row.value.get(query.field_path)==query.value]
        elif query.op_string=='>=':self.rows=[row for row in self.rows if row.value.get(query.field_path) is not None and row.value[query.field_path]>=query.value]
        return self
    def limit(self,bound):self.bound=bound;return self
    def stream(self,**kwargs):return iter(self.rows[:self.bound])
class Client:
    closed=False
    def __init__(self,collections):self.collections=collections
    def collection(self,name):return Collection(self.collections.get(name,[]))
    def close(self):self.closed=True

def transport(request):return httpx.Response(200,json=[])


def test_readonly_adapter_preserves_attributed_unknown_level_and_private_upload_shape():
    value=dict(shop_id='PRIVATE-SHOP',sha256='c'*64,lat=0.,lng=0.,received_at=NOW,telegram_date=NOW,confirmed_at=NOW,location_attribution='confirmed_shared',evidence_status='unverified',is_demo=False,media_id='PRIVATE-MEDIA',sender_hash='PRIVATE-SENDER')
    point=json.loads(Path('infra/data/safe_points.json').read_text())[0]
    client=Client({'photo_reports':[Snapshot('a'*32,value)],'safe_points':[Snapshot(point['safe_point_id'],point)]})
    reader=PublicCheckReader(client,transport=httpx.MockTransport(transport),clock=lambda:NOW)
    result=asyncio.run(reader.read(LOCATION))
    assert len(result.observations)==1 and result.observations[0].level is None
    assert result.level is None and result.destination_status=='available'
    for private in ('PRIVATE-SHOP','PRIVATE-MEDIA','PRIVATE-SENDER','sha256'):
        assert private not in result.model_dump_json()


def test_report_and_destination_scan_overflow_are_unavailable_not_truncated_success():
    rows=[Snapshot(str(i),{'is_demo':False,'received_at':NOW}) for i in range(1001)]
    reader=PublicCheckReader(Client({'photo_reports':rows,'safe_points':rows}),transport=httpx.MockTransport(transport),clock=lambda:NOW)
    result=asyncio.run(reader.read(LOCATION))
    assert not result.observations and not result.destinations and result.destination_status=='unavailable'
    assert next(s for s in result.sources if s.source=='shop_report').status=='unavailable'
    assert result.status=='partial'


def test_oversized_valid_official_json_is_bounded_unavailable():
    reader=PublicCheckReader(Client({}),transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b' '*5_000_001+b'[]')),clock=lambda:NOW)
    result=asyncio.run(reader.read(LOCATION))
    assert all(s.status=='unavailable' for s in result.sources if s.source in ('jps','met'))


def test_factory_uses_configured_cutoff_scope_and_does_not_construct_model_or_sinks():
    from datetime import timedelta
    client=Client({})
    with patch('api.tools.firestore.create_firestore_client',return_value=client) as factory:
        reader=create_public_check_reader(Settings(official_max_age_minutes=30,destination_search_radius_m=15000))
    assert reader.official_max_age==timedelta(minutes=30) and reader.destination_radius_m==15000
    assert factory.call_count==1
    reader.close();assert client.closed


def test_expired_intent_cannot_steal_registered_location_and_danger_is_exact_existing_template():
    assert location_routing('waiting_location',registered_flow_waiting=False)=='public_check'
    assert location_routing('waiting_location',registered_flow_waiting=True)=='existing_flow'
    assert location_routing('expired',registered_flow_waiting=False)=='existing_flow'
    assert location_routing('complete',registered_flow_waiting=False)=='existing_flow'
    result=project_check(LOCATION,(source(warning(level='danger')),),(),(),now=NOW)
    from api.alert_composer import render_danger
    for language in ('en','ms','zh','ta','bn','ne','my','id'):
        assert fixed_check_danger(result,language)==render_danger(language,False,None)
    assert fixed_check_danger(project_check(LOCATION,(),(),(),now=NOW),'en') is None


def test_bounded_reader_handles_actual_http_decompressed_gzip_json():
    import gzip
    reader=PublicCheckReader(Client({}),transport=httpx.MockTransport(lambda r:httpx.Response(200,content=gzip.compress(b'[]'),headers={'content-encoding':'gzip'})),clock=lambda:NOW)
    result=asyncio.run(reader.read(LOCATION))
    assert all(s.status=='empty' for s in result.sources if s.source in ('jps','met'))


def test_actual_reader_query_keeps_earliest_known_hash_provenance_before_age_filtering():
    from datetime import timedelta
    value=dict(shop_id='private',sha256='c'*64,lat=0.,lng=0.,received_at=NOW-timedelta(minutes=31),telegram_date=NOW-timedelta(minutes=32),confirmed_at=NOW-timedelta(minutes=30),location_attribution='confirmed_shop',evidence_status='positive',level='warning',is_demo=False)
    newer={**value,'received_at':NOW-timedelta(minutes=1),'telegram_date':NOW-timedelta(minutes=2),'confirmed_at':NOW}
    reader=PublicCheckReader(Client({'photo_reports':[Snapshot('a'*32,value),Snapshot('b'*32,newer)]}),transport=httpx.MockTransport(transport),clock=lambda:NOW)
    result=asyncio.run(reader.read(LOCATION))
    assert not result.observations and result.level is None
