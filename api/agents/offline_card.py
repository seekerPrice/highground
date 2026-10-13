"""Actual ADK constrained card wording selection; no property/place authority."""
import json
from uuid import uuid4
from google.adk.events import Event,EventActions
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig
from google.adk.models import LlmResponse
from google.adk.models.google_llm import Gemini
from google.genai import types
from api.agents.coordinator import create_coordinator
from api.agents.sessions import create_session_service
from api.offline_card import CardChoice
from api.tools.firestore import create_async_firestore_client,close_async_firestore_client
from api.tools.gemini import create_vertex_client

class CardSelector:
    def __init__(self,settings,*,model=None,root_collection='highground-card-adk'):
        self.settings,self.model,self.root_collection=settings,model,root_collection
        self._vertex=None

    async def __call__(self,context):
        if self.model is None:
            if not self.settings.gemini_fast_model.strip():raise ValueError('Configured card model unavailable')
            if self._vertex is None:self._vertex=create_vertex_client(self.settings)
        model=self.model or Gemini(model=self.settings.gemini_fast_model,client=self._vertex)
        client=create_async_firestore_client(self.settings)
        sessions=create_session_service(self.settings,client=client,root_collection=self.root_collection)
        root=create_coordinator(self.settings,model=model)
        root.instruction='You are highground_coordinator. Transfer immediately to offline_card_agent for approved wording selection only. No safety/property actions are authorized.'
        def route(callback_context,llm_request):
            return LlmResponse(content=types.Content(role='model',parts=[types.Part.from_function_call(name='transfer_to_agent',args={'agent_name':'offline_card_agent'})]))
        root.before_model_callback=route
        agent=root.sub_agents[1];agent.name='offline_card_agent';agent.tools=[]
        facts={'language':context.language,'inventory_available':bool(context.items),'listed_destinations_available':bool(context.parking or context.shelter),'simulation':context.is_demo}
        agent.instruction='Choose only approved localized title/footer keys. Prefer card_title_actions when inventory is available, otherwise card_title. Return JSON {"title":"card_title or card_title_actions","footer":"card_footer"}. Do not generate advice, amounts, places or times. Validated context: '+json.dumps(facts)
        agent.output_schema=CardChoice;agent.output_key='card_choice';agent.disallow_transfer_to_parent=True;agent.disallow_transfer_to_peers=True
        for node in [root,*root.sub_agents]:
            node.generate_content_config=types.GenerateContentConfig(max_output_tokens=1024,thinking_config=types.ThinkingConfig(thinking_level='LOW'),http_options=types.HttpOptions(timeout=15000,retry_options=types.HttpRetryOptions(attempts=1)))
        kwargs={'app_name':'highground_card','user_id':'wording-'+context.language,'session_id':context.card_id+'-'+uuid4().hex}
        runner=Runner(app_name='highground_card',agent=root,session_service=sessions)
        try:
            await sessions.create_session(**kwargs,state={'card_id':context.card_id,'simulation':context.is_demo})
            choice=None
            message=types.Content(role='user',parts=[types.Part.from_text(text='Select approved offline-card wording keys. No actions or facts may be generated.')])
            async for event in runner.run_async(user_id=kwargs['user_id'],session_id=kwargs['session_id'],new_message=message,run_config=RunConfig(max_llm_calls=3)):
                if event.author=='offline_card_agent' and event.is_final_response() and event.content:
                    raw=''.join(part.text or '' for part in event.content.parts or [])
                    if len(raw)>500 or set(json.loads(raw))!={'title','footer'}:raise ValueError('Invalid card selector output')
                    choice=CardChoice.model_validate_json(raw,strict=True)
            if choice is None:raise ValueError('Card agent returned no approved wording')
            session=await sessions.get_session(**kwargs)
            await sessions.append_event(session,Event(author='card_validator',actions=EventActions(state_delta={'validated_card_choice':choice.model_dump()})))
            return choice
        finally:
            try:await runner.close()
            finally:await close_async_firestore_client(client)

    async def close(self):
        if self._vertex:
            try:await self._vertex.aio.aclose()
            finally:self._vertex.close();self._vertex=None
