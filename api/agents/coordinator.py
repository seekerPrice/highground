"""Actual ADK root/sub-agent structure; domain actions remain disabled stubs."""
from typing import TYPE_CHECKING

from google import genai
from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.genai import types

from api.agents import stubs

if TYPE_CHECKING:
    from api.config import Settings

BOUNDARY = (
    'You are the HighGround Task 6 skeleton. All tools return not_implemented. '
    'Never claim an alert, inventory, report, risk decision or destination exists. '
    'Label simulated inputs and decisions SIMULATION. Do not generate Danger advice; '
    'Danger dispatch must later use committed fixed templates in deterministic tools. '
    'Never claim a route/site is safe or media genuine. If a tool is unavailable, '
    'explain that the feature is not implemented. Do not infer success from a stub. '
)


def create_coordinator(settings: 'Settings', *, model: BaseLlm | None = None,
                       loss_model: BaseLlm | None = None,
                       client: genai.Client | None = None) -> LlmAgent:
    """Caller owns an injected client; production must explicitly close its client."""
    if model is None:
        if not settings.gemini_fast_model.strip() or not settings.gemini_pro_model.strip():
            raise ValueError('GEMINI_FAST_MODEL and GEMINI_PRO_MODEL are required for ADK')
        if client is None:
            raise ValueError('Pass an owned Vertex client from create_vertex_client(settings)')
        model = Gemini(model=settings.gemini_fast_model, client=client)
        loss_model = Gemini(model=settings.gemini_pro_model, client=client)
    loss_model = loss_model or model
    config = types.GenerateContentConfig(
        max_output_tokens=1024, temperature=0,
        thinking_config=types.ThinkingConfig(thinking_level='LOW'),
        http_options=types.HttpOptions(timeout=50000,
                                       retry_options=types.HttpRetryOptions(attempts=1)),
    )
    triage = LlmAgent(
        name='triage_agent', model=model, description='Official observations and shop-photo triage boundary.',
        instruction=BOUNDARY+'For official warnings or photo reports, inspect available triage tools. '
                    'No risk classification is implemented here; after inspecting, transfer to alert_agent for its stub boundary.',
        tools=[stubs.verify_flood_photo, stubs.get_official_warnings, stubs.get_recent_reports],
        generate_content_config=config,
    )
    alert = LlmAgent(
        name='alert_agent', model=model, description='Disabled recipient alert and destination boundary.',
        instruction=BOUNDARY+'Dispatch is disabled. Inspect get_shop_profile only if a simulated shop is provided. '
                    'Return an explicit not_implemented result; never call dispatch as if it were live.',
        tools=[stubs.find_shops_in_radius, stubs.get_shop_profile, stubs.get_lift_first_list,
               stubs.find_nearest_safe_point, stubs.render_offline_card, stubs.send_telegram, stubs.log_alert],
        generate_content_config=config,
    )
    loss = LlmAgent(
        name='loss_agent', model=loss_model, description='Inventory and post-flood loss-report boundary.',
        instruction=BOUNDARY+'Inventory videos and after-flood comparison requests belong here. '
                    'Report no valuations because all tools are stubs.',
        tools=[stubs.build_inventory, stubs.rank_lift_first, stubs.compare_inventories,
               stubs.estimate_water_mark, stubs.create_report],
        generate_content_config=config,
    )
    return LlmAgent(
        name='highground_coordinator', model=model,
        instruction=BOUNDARY+'Route official warnings and shop flood photos to triage_agent, '
                    'recipient alert context to alert_agent, inventory/loss context to loss_agent. '
                    'For a fake warning demonstration, transfer to triage_agent first.',
        sub_agents=[triage, alert, loss], generate_content_config=config,
    )
