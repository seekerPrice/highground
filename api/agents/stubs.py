"""Task 6 tool boundaries. Every result is explicitly unimplemented.

These stubs perform no network requests, persistence, model calls or dispatch.
They never echo private input values into their responses.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StubResult(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    status: Literal['not_implemented'] = 'not_implemented'
    feature: str
    detail: str = 'Task 6 skeleton only; no decision or action was performed.'


def _stub(feature: str) -> dict[str, str]:
    return StubResult(feature=feature).model_dump()


def verify_flood_photo(gcs_uri: str) -> dict[str, str]:
    """Flood-photo verification boundary; not implemented."""
    return _stub('verify_flood_photo')


def get_official_warnings() -> dict[str, str]:
    """Official-source integration boundary; not implemented in the ADK skeleton."""
    return _stub('get_official_warnings')


def get_recent_reports(lat: float, lng: float, radius_m: int, minutes: int) -> dict[str, str]:
    """Recent geographically scoped reports boundary; not implemented."""
    return _stub('get_recent_reports')


def find_shops_in_radius(lat: float, lng: float, radius_m: int) -> dict[str, str]:
    """Shop targeting boundary; not implemented."""
    return _stub('find_shops_in_radius')


def get_shop_profile(shop_id: str) -> dict[str, str]:
    """Shop profile boundary; not implemented."""
    return _stub('get_shop_profile')


def get_lift_first_list(shop_id: str) -> dict[str, str]:
    """Lift-first list boundary; not implemented."""
    return _stub('get_lift_first_list')


def find_nearest_safe_point(lat: float, lng: float, type: str) -> dict[str, str]:
    """Sourced listed-destination boundary; not implemented."""
    return _stub('find_nearest_safe_point')


def render_offline_card(shop_id: str, event_id: str) -> dict[str, str]:
    """Offline card boundary; no card generation in the skeleton."""
    return _stub('render_offline_card')


def send_telegram(chat_id: str, text: str) -> dict[str, str]:
    """Disabled alert dispatch boundary; never sends Telegram messages."""
    return _stub('send_telegram')


def log_alert(event_id: str) -> dict[str, str]:
    """Alert logging boundary; not implemented."""
    return _stub('log_alert')


def build_inventory(video_gcs_uri: str) -> dict[str, str]:
    """Video inventory boundary; not implemented."""
    return _stub('build_inventory')


def rank_lift_first(inventory_id: str) -> dict[str, str]:
    """Deterministic lift-first boundary; not implemented."""
    return _stub('rank_lift_first')


def compare_inventories(before_id: str, after_video_gcs_uri: str) -> dict[str, str]:
    """Loss-comparison boundary; not implemented."""
    return _stub('compare_inventories')


def estimate_water_mark(photo_gcs_uri: str) -> dict[str, str]:
    """Unimplemented roadmap water-mark boundary; no measurement performed."""
    return _stub('estimate_water_mark')


def create_report(shop_id: str, comparison: str) -> dict[str, str]:
    """Loss-report boundary; not implemented."""
    return _stub('create_report')
