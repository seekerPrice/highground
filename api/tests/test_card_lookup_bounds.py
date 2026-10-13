"""A bounded scan must never turn incomplete data into authorization/geography."""
from types import SimpleNamespace
from api.photo_store import PhotoStore
from api.destinations import DestinationLookup

class Document:
    def __init__(self,identity,value):self.id,self.value=identity,value
    def to_dict(self):return self.value

class Collection:
    def __init__(self,rows):self.rows,self.bound=rows,None
    def limit(self,bound):self.bound=bound;return self
    def stream(self,**kwargs):return iter(self.rows[:self.bound])

class Client:
    def __init__(self,rows):self.rows=rows
    def collection(self,name):return Collection(self.rows)


def test_membership_scan_overflow_cannot_hide_second_membership_and_authorize():
    rows=[Document('owner',{'recipients':[{'telegram_chat_id':101,'language':'en'}]})]
    rows.extend(Document(str(i),{'recipients':[]}) for i in range(999))
    rows.append(Document('hidden-second',{'recipients':[{'telegram_chat_id':101,'language':'en'}]}))
    store=PhotoStore(Client(rows),'test',risks=SimpleNamespace())
    assert store.shop_for_sender(101) is None


def test_destination_scan_overflow_does_not_select_partial_nearest():
    import json
    from pathlib import Path
    point=json.loads(Path('infra/data/safe_points.json').read_text())[0]
    rows=[Document(point['safe_point_id'],point)]
    rows.extend(Document(str(i),{}) for i in range(1000))
    assert DestinationLookup(Client(rows)).nearest(point['lat'],point['lng'],('parking',)) is None
