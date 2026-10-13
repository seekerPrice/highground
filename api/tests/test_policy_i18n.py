"""Generated policy catalogs use exact placeholders and bounded public replies."""
import asyncio
from datetime import date
from api.i18n import LANGUAGES,text,catalog
from api.policy import PolicyService,POLICY_EN
from api.policy_models import compare_policy
from api.tests.test_policy_models import assessment,BASE

class Store:
    def __init__(self,shop):self.shop=shop
    def shop_for_sender(self,sender):return self.shop
    def danger_active(self,shop):return False

def test_all_generated_policy_reply_variants_and_callback_data_fit_limits():
    async def run():
        for language in LANGUAGES:
            current=catalog(language)
            assert set(POLICY_EN).issubset(current)
            shop=dict(shop_id='synthetic',lat=3.,lng=101.,language=language,is_demo=True)
            service=PolicyService(Store(shop),None,None,translate=text)
            long=assessment(insurer='A'*120,policy_type='B'*120,evidence_quote='Flood is included. '+('C'*281))
            job=dict(shop,intake_id='a'*32,choice='keep',choice_frozen=True,disclosed=True,mode='photos',status='complete',originals=[{}]*5,assessment=long.model_dump(),deletion_pending=False)
            for changes in ({},{'flood_covered':'no','coverage_evidence':'excluded','evidence_quote':'Flood is excluded.'},{'flood_covered':'unclear','coverage_evidence':'unclear','evidence_quote':None},{'sum_insured_rm':None},{'expiry_date':None}):
                value=assessment(**(dict(insurer='A'*120,policy_type='B'*120,evidence_quote=long.evidence_quote)|changes))
                job.update(assessment=value.model_dump(),comparison=compare_policy(value,BASE,date(2026,10,13)).model_dump(mode='json'))
                reply=await service._result(job,123)
                assert len(reply.text)<=4096 and 'estimated_shortfall' not in reply.text
                assert current['simulation_label'] in reply.text
                if not current['_reviewed']:assert current['translation_notice'] in reply.text
                for row in reply.reply_markup['inline_keyboard']:
                    for button in row:assert len(button['callback_data'].encode())<=64
            job['choice_frozen']=False
            assert len((await service._reply(job,'policy_disclosure',sender=123)).text)<=4096
    asyncio.run(run())
