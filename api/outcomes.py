"""Pure owner-response, due-time and denominator decisions."""
from datetime import datetime
from api.outcome_models import OutcomeEpisode,OwnerOutcome,OutcomePrompt,PromptDecision,OutcomeCoverage


def first_owner_response(previous:OwnerOutcome|None,episode:OutcomeEpisode,*,actor_hash:str,actor_shop_id:str,actor_role:str,current_owner_hash:str,answer:str,observed_at:datetime,answered_at:datetime,depth_cm:int|None=None,entrypoint='alert_response',origin='telegram_owner')->OwnerOutcome:
    from hashlib import sha256
    if actor_role!='owner' or actor_shop_id!=episode.shop_id or actor_hash!=current_owner_hash:raise ValueError('Current owner authorization required')
    if observed_at<episode.started_at or (episode.closed_at is not None and observed_at>episode.closed_at):raise ValueError('Observation must match confirmed episode')
    if previous is not None:
        if (previous.shop_id,previous.episode_id,previous.area,previous.is_demo,previous.scenario_generation)!=(episode.shop_id,episode.episode_id,episode.area,episode.is_demo,episode.scenario_generation):raise ValueError('First response episode mismatch')
        return previous
    return OwnerOutcome(response_id=sha256(f'{episode.is_demo}:{episode.scenario_generation}:{episode.shop_id}:{episode.episode_id}'.encode()).hexdigest(),shop_id=episode.shop_id,episode_id=episode.episode_id,area=episode.area,owner_hash=actor_hash,answer=answer,observed_at=observed_at,answered_at=answered_at,depth_cm=depth_cm,entrypoint=entrypoint,origin=origin,is_demo=episode.is_demo,scenario_generation=episode.scenario_generation)


def prompt_due(episode:OutcomeEpisode,now:datetime,*,current_owner_hash:str|None,current_generation:int|None=None,active_danger:bool=False,ask_after_hours:float=6.)->PromptDecision:
    import math
    from datetime import timedelta
    from api.outcome_models import PromptDecision
    if now.tzinfo is None or now.utcoffset() is None:raise ValueError('Due clock must be aware')
    if type(active_danger) is not bool or type(ask_after_hours) not in (int,float) or not math.isfinite(ask_after_hours) or ask_after_hours<=0:raise ValueError('Invalid outcome schedule')
    try:delay=timedelta(hours=ask_after_hours)
    except OverflowError:raise ValueError('Invalid outcome schedule') from None
    if episode.is_demo and current_generation!=episode.scenario_generation:return PromptDecision(due=False,reason='obsolete_scenario',due_at=None)
    if current_owner_hash is None:return PromptDecision(due=False,reason='no_owner',due_at=None)
    accepted=[row.accepted_at for row in episode.deliveries if row.level in ('warning','danger') and row.status=='accepted' and row.provenance=='telegram_api']
    candidates=([min(accepted)+delay] if accepted else [])+([episode.closed_at] if episode.closed_at else [])
    due_at=min(candidates) if candidates else None
    reason='active_danger' if active_danger else 'no_accepted_alert_or_closure' if due_at is None else 'due' if now>=due_at else 'waiting'
    return PromptDecision(due=reason=='due',reason=reason,due_at=due_at)


def response_matches_episode(response:OwnerOutcome,episode:OutcomeEpisode)->bool:
    return (response.shop_id,response.episode_id,response.area,response.is_demo,response.scenario_generation)==(episode.shop_id,episode.episode_id,episode.area,episode.is_demo,episode.scenario_generation) and response.observed_at>=episode.started_at and (episode.closed_at is None or response.observed_at<=episode.closed_at)


def first_outcomes(responses:tuple[OwnerOutcome,...])->dict[tuple[bool,int|None,str,str],OwnerOutcome]:
    if len(responses)>1000:raise ValueError('Outcome scope exceeds bound')
    first={}
    for response in sorted(responses,key=lambda row:(row.answered_at,row.response_id)):
        key=(response.is_demo,response.scenario_generation,response.shop_id,response.episode_id)
        first.setdefault(key,response)
    return first


def outcome_coverage(episodes:tuple[OutcomeEpisode,...],responses:tuple[OwnerOutcome,...],prompts:tuple[OutcomePrompt,...],*,synthetic_shop_ids:set[str],generation:int)->OutcomeCoverage:
    from api.outcome_models import OutcomeCoverage
    if len(episodes)>1000 or len(prompts)>1000 or len(synthetic_shop_ids)>50:raise ValueError('Outcome coverage exceeds bound')
    eligible={(row.shop_id,row.episode_id):row for row in episodes if row.is_demo and row.scenario_generation==generation and row.shop_id in synthetic_shop_ids}
    first=first_outcomes(responses)
    selected=[row for (_,gen,shop,episode),row in first.items() if row.is_demo and gen==generation and (shop,episode) in eligible and response_matches_episode(row,eligible[(shop,episode)])]
    accepted=set();virtual=set();unknown=set();fixtures=set()
    for prompt in prompts:
        key=(prompt.shop_id,prompt.episode_id)
        if key not in eligible or not prompt.is_demo or prompt.scenario_generation!=generation:continue
        if prompt.status=='accepted' and prompt.provenance=='telegram_api':accepted.add(key)
        elif prompt.status=='simulated' and prompt.provenance=='local_virtual':virtual.add(key)
        elif prompt.status=='simulated' and prompt.provenance=='synthetic_fixture':fixtures.add(key)
        elif prompt.status in ('sending','uncertain'):unknown.add(key)
    counts={answer:sum(row.answer==answer for row in selected) for answer in ('no','street_only','entrance','inside')}
    return OutcomeCoverage(eligible_shop_episodes=len(eligible),accepted_prompts=len(accepted),virtual_prompts=len(virtual),uncertain_or_sending_prompts=len(unknown),responses=len(selected),fixture_prompts=len(fixtures),fixture_responses=sum(row.origin=='synthetic_fixture' for row in selected),missing_unknown=len(eligible)-len(selected),**counts)
