"""Server-owned local demo generations; reset never deletes immutable facts."""
from datetime import UTC, datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api.active_risk import ActiveRiskStore
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


FIXTURE_ORIGIN='highground-task16-v1'
SHOP_IDS=tuple(f'demo-t16-{i}' for i in range(1,7))


class ScenarioResetBusy(ValueError):
    pass


def alerts_only_fixture(shop_id:str,record:dict) -> bool:
    """Only owned fixture bindings carry alert membership without media ownership.

    Older bindings predate explicit scope; their exact owned provenance retains
    the same documented boundary. Ordinary synthetic registrations stay ordinary.
    """
    scoped=record.get('recipient_scope')=='alerts_confirmations_only' or (record.get('recipient_scope') is None and record.get('binding_provenance')=='explicit_operator_registered_owner')
    return bool(scoped and shop_id in SHOP_IDS and record.get('is_demo') is True and record.get('fixture_origin')==FIXTURE_ORIGIN)


def scenario_collection(shops: str) -> str:
    return shops.removesuffix('shops')+'demo_scenario'


def current_scenario(client:firestore.Client, collection:str, transaction:firestore.Transaction|None=None) -> dict:
    return client.collection(collection).document('current').get(transaction=transaction).to_dict() or {}


def event_is_current(event:dict, scenario:dict,shop_id:str|None=None) -> bool:
    return not event.get('is_demo') or (scenario.get('state','ready')=='ready'
        and event.get('scenario_generation',0)==scenario.get('generation',0)
        and (shop_id is None or scenario.get('fixture_shop_ids') is None or shop_id in scenario['fixture_shop_ids']))


class DemoScenarioStore:
    def __init__(self, client:firestore.Client, risks:'ActiveRiskStore', *, prefix:str='') -> None:
        self.client,self.risks,self.prefix=client,risks,prefix
        self.ref=client.collection(prefix+'demo_scenario').document('current')

    def reset(self, request_id: str) -> dict:
        now=datetime.now(UTC)
        receipt=self.client.collection(self.prefix+'demo_resets').document(request_id)
        # Capture only a bounded synthetic scope. The transactional fence precedes
        # all mutations, and all creators/readers use the same scenario document.
        @firestore.transactional
        def start(tx):
            state=self.ref.get(transaction=tx).to_dict() or {}
            previous=receipt.get(transaction=tx).to_dict()
            if previous:return previous
            if state.get('state')=='resetting':
                if state['reset_request_id']!=request_id:raise ScenarioResetBusy('Demo reset in progress; retry the same request')
                return state
            state={**state,'state':'resetting','reset_request_id':request_id,
                   'generation':state.get('generation',0),'next_generation':state.get('generation',0)+1,
                   'shop_ids':[],'scope_ready':False,'done':[],'reset_started_at':now}
            tx.set(self.ref,state)
            return state
        state=start(self.client.transaction())
        if state.get('status')=='reset':return state
        if not state.get('scope_ready'):
            shops=self._shop_ids()
            if len(shops)>50:raise ValueError('Demo reset scope exceeds bound')
            @firestore.transactional
            def capture(tx):
                current=self.ref.get(transaction=tx).to_dict()
                if current.get('reset_request_id')!=request_id or current.get('state')!='resetting':return current
                if current.get('scope_ready'):return current
                tx.update(self.ref,{'shop_ids':shops,'scope_ready':True})
                return {**current,'shop_ids':shops,'scope_ready':True}
            state=capture(self.client.transaction())
        # An already-started external request cannot be unsent. Do not expose the
        # next ready generation until its lease drains; expiry is explicitly ambiguous.
        ambiguous=[]
        for shop_id in state['shop_ids']:
            lease=self.client.collection(self.risks.deliveries).document(shop_id).get().to_dict() or {}
            if lease.get('until',now)>now:return self._result(state,'resetting',[])
            if lease.get('owner') and not lease.get('released_at'):ambiguous.append(shop_id)
        for shop_id in state['shop_ids']:
            if shop_id in state['done']:continue
            self.risks.reset_demo(shop_id,reset_request_id=request_id,reset_generation=state['generation'])
            state=self.ref.get().to_dict()
        @firestore.transactional
        def finish(tx):
            current=self.ref.get(transaction=tx).to_dict()
            saved=receipt.get(transaction=tx).to_dict()
            if saved:return saved
            if current.get('reset_request_id')!=request_id or set(current['done'])!=set(current['shop_ids']):raise ScenarioResetBusy('Demo reset incomplete')
            ready={**current,'generation':current['next_generation'],'state':'ready','started_at':datetime.now(UTC)}
            result=self._result(ready,'reset',ambiguous)
            tx.set(self.ref,ready);tx.create(receipt,result)
            return result
        return finish(self.client.transaction())

    def _shop_ids(self) -> list[str]:
        state=self.ref.get().to_dict() or {}
        if state.get('fixture_shop_ids') is not None:
            identities=state['fixture_shop_ids']
            if len(identities)>6 or len(set(identities))!=len(identities) or not set(identities).issubset(SHOP_IDS):raise ValueError('Fixture reset scope exceeds six shops')
            existing=[]
            for identity in identities:
                shop=self.client.collection(self.prefix+'shops').document(identity).get(timeout=8,retry=None).to_dict() or {}
                if shop.get('is_demo') is True and shop.get('fixture_origin')==FIXTURE_ORIGIN:existing.append(identity)
            return existing
        return [doc.id for doc in self.client.collection(self.prefix+'shops').where(filter=FieldFilter('is_demo','==',True)).limit(51).stream()]

    @staticmethod
    def _result(state:dict,status:str,ambiguous:list[str]) -> dict:
        return dict(status=status,generation=state.get('generation',0),
                    scenario_started_at=state.get('started_at').isoformat() if state.get('started_at') else None,
                    shops_reset=len(state['done']),inflight_outcomes_unknown=len(ambiguous),
                    delivery_note='Already-started external sends cannot be unsent; expired unreleased sends have unknown outcomes.')
