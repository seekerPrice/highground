"""Canonical alert facts and absolute fixed-template Danger rendering boundary."""
import asyncio
from datetime import timedelta
from zoneinfo import ZoneInfo

import httpx
from google.genai.errors import APIError
from pydantic import ValidationError

from api.dispatch_models import ActionSnapshot, Destination, Shop
from api.agents.warning_selector import WarningStructure
from api.tools.geo import distance_m

def _localized(language: str, key: str, **values) -> str:
    from api.i18n import text
    return text(language, key, **values)


def snapshot_actions(event: dict, shop: Shop, *, vehicle_minutes: int = 15, stock_minutes: int = 30) -> ActionSnapshot:
    if type(vehicle_minutes) is not int or type(stock_minutes) is not int or not 0 < vehicle_minutes < stock_minutes:
        raise ValueError('Action targets require positive ordered integer minutes')
    if event['level'] != 'warning':
        return ActionSnapshot()
    items = tuple(shop.lift_first) if shop.baseline_inventory_id else ()
    return ActionSnapshot(
        inventory_id=shop.baseline_inventory_id, items=items,
        estimated_value_rm=sum(item.value_rm for item in items),
        vehicle_type=shop.vehicle_type if shop.has_vehicle else None,
        vehicle_target_at=event['created_at']+timedelta(minutes=vehicle_minutes) if shop.has_vehicle else None,
        stock_target_at=event['created_at']+timedelta(minutes=stock_minutes),
    )


def render_danger(language: str, is_demo: bool, destination: Destination | None = None) -> tuple[str, dict | None]:
    from api.i18n import danger_text
    rendered = danger_text(language, is_demo=is_demo,
                           safe_point_name=destination.name if destination else None,
                           route_link=destination.route_link if destination else None)
    if len(rendered) > 4096:
        raise ValueError('Committed Danger template exceeds Telegram limit')
    markup = None
    if destination:
        markup = {'inline_keyboard': [[{'text': _localized(language, 'route_button'), 'url': destination.route_link}]]}
    return rendered, markup


class AlertComposer:
    def __init__(self, *, selector=None,
                 vehicle_minutes: int = 15, stock_minutes: int = 30, selection_budget_seconds: float = 5) -> None:
        self.selector = selector
        if type(vehicle_minutes) is not int or type(stock_minutes) is not int or not 0 < vehicle_minutes < stock_minutes:
            raise ValueError('Action targets require positive ordered integer minutes')
        if not 0 < selection_budget_seconds <= 5:
            raise ValueError('Warning selection budget must be bounded')
        self.selection_budget_seconds = selection_budget_seconds
        self.vehicle_minutes, self.stock_minutes = vehicle_minutes, stock_minutes
        self._choices: dict[tuple[str, str], str] = {}

    async def prepare(self, event: dict, languages: set[str], *, has_inventory: bool = False,
                      has_vehicle: bool = False) -> None:
        if event['level'] != 'warning' or self.selector is None:
            return
        async def select(language: str) -> None:
            key = (event['event_id'], language)
            if key in self._choices:
                return
            self._choices[key] = 'warning_intro_fallback'
            for attempt in range(2):
                try:
                    result = await self.selector(event, language, has_inventory, has_vehicle)
                    result = WarningStructure.model_validate(result, strict=True)
                    self._choices[key] = result.structure
                    return
                except (ValidationError, ValueError, TimeoutError, httpx.TransportError):
                    if attempt == 1:
                        return
                except APIError as error:
                    if attempt == 1 or not (isinstance(error.code, int) and (error.code == 429 or 500 <= error.code < 600)):
                        return
                except Exception:
                    return
        # One total event budget, regardless of recipients/languages; cancellation is awaited.
        try:
            async with asyncio.timeout(self.selection_budget_seconds):
                await asyncio.gather(*(select(language) for language in languages))
        except Exception:
            pass

    async def compose(self, event: dict, shop: Shop, language: str) -> tuple[str, ActionSnapshot, dict | None]:
        # Must precede every model/stock/vehicle branch: no generated Danger text.
        if event['level'] == 'danger':
            rendered, markup = render_danger(language, event['is_demo'])
            return rendered, ActionSnapshot(), markup
        snapshot = snapshot_actions(event, shop, vehicle_minutes=self.vehicle_minutes, stock_minutes=self.stock_minutes)
        if event['level'] == 'watch':
            body = _localized(language, 'watch_alert', reason=_localized(language, 'situation_watch'))
        else:
            structure = self._choices.get((event['event_id'], language), 'warning_intro_fallback')
            body = _localized(language, structure, reason=_localized(language, 'situation_warning'))
            meters = distance_m(event['lat'], event['lng'], shop.lat, shop.lng)
            parts = [body, _localized(language, 'warning_distance', distance_m=f'{meters:.0f}')]
            if snapshot.items:
                parts.append(_localized(language, 'lift_first_heading'))
                for item in snapshot.items:
                    parts.append(_localized(language, 'item_estimate_line', item_name=item.item_name,
                                            qty=f'{item.qty:g}', value_rm=f'{item.value_rm:.2f}'))
                parts.append(_localized(language, 'stock_value_estimate', value_rm=f'{snapshot.estimated_value_rm:.2f}'))
            else:
                parts.append(_localized(language, 'inventory_unavailable'))
            if snapshot.vehicle_target_at:
                parts.append(_localized(language, 'vehicle_target_unavailable', vehicle_type=_localized(language, snapshot.vehicle_type) if snapshot.vehicle_type else '-',
                                        deadline=snapshot.vehicle_target_at.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).strftime('%d %b %H:%M MYT')))
            parts.extend([
                _localized(language, 'stock_action_target', deadline=snapshot.stock_target_at.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).strftime('%d %b %H:%M MYT')),
                _localized(language, 'action_target_note'), _localized(language, 'rm_estimate_note'),
                _localized(language, 'destination_unavailable'),
            ])
            body = '\n'.join(parts)
        pieces = [_localized(language, 'simulation_label')] if event['is_demo'] else []
        pieces.append(body)
        # Translation notice belongs inside Danger templates; ordinary messages use a fixed notice.
        from api.i18n import catalog
        if not catalog(language)['_reviewed']:
            pieces.append(_localized(language, 'translation_notice'))
        pieces.append(_localized(language, 'emergency_footer'))
        rendered = '\n'.join(pieces)
        if len(rendered) > 4096:
            # Never silently truncate the displayed inventory snapshot.
            raise ValueError('Alert exceeds Telegram text limit')
        return rendered, snapshot, None


def send_alert(telegram, alert: dict) -> int:
    """Wrapper enforces Danger again, even if persisted/model text was replaced."""
    if alert['level'] == 'danger':
        snapshot = ActionSnapshot.model_validate(alert['snapshot'])
        text, markup = render_danger(alert['language'], alert['is_demo'], snapshot.destination)
    else:
        text, markup = alert['text'], alert.get('reply_markup')
        if len(text) > 4096:
            raise ValueError('Alert exceeds Telegram text limit')
    return telegram.send_message(alert['telegram_chat_id'], text, reply_markup=markup)
